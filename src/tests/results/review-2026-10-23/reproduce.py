"""只使用本地替身复现审查边界；不调用设备或模型API、不修改产品代码。"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path

from mcp_eval.config import validate_config
from mcp_eval.device import command_for_case
from mcp_eval.judge import judge_record
from mcp_eval.model_loop import ModelLoop
from mcp_eval.providers.base import ProviderResponse
from mcp_eval.providers.openai_compat import OpenAICompatProvider
from mcp_eval.records import EvalRecord

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TOOLS = [{"name": "service.setTemp", "inputSchema": {
    "type": "object", "properties": {"temperature": {"type": "number", "minimum": 16, "maximum": 30}},
    "required": ["temperature"], "additionalProperties": False}}]
CASE = {"case_id": "M01", "level": "L2", "category": "negative", "action": "model_task",
        "service": "auto", "task": "不要调用任何工具，仅回答你好", "expected_source": "synthetic review probe",
        "assertions": [{"type": "no_tool_call"}]}


class Executor:
    channel = "replay"
    source_type = "synthetic"

    def __init__(self):
        self.calls = []

    def __call__(self, name, arguments, *, timeout):
        self.calls.append({"name": name, "arguments": copy.deepcopy(arguments)})
        return EvalRecord(run_id="probe", case_id="M01", channel="replay", action="tools_call",
                          service="auto", tool=name, arguments=arguments, trace_complete=True,
                          execution_status="completed", source_type="synthetic",
                          response_raw={"jsonrpc": "2.0", "id": 1, "result": {"isError": False}})


def response(arguments, finish_reason="tool_calls"):
    return OpenAICompatProvider._parse({"choices": [{"finish_reason": finish_reason, "message": {
        "content": None, "tool_calls": [{"id": "call-1", "type": "function", "function": {
            "name": "service_setTemp", "arguments": arguments}}]}}]})


def nonfinite_dispatch():
    parsed = response('{"temperature": NaN}')

    class Provider:
        rounds = 0

        def chat(self, *args, **kwargs):
            self.rounds += 1
            return parsed if self.rounds == 1 else ProviderResponse(content="完成", finish_reason="stop")

    executor = Executor()
    record = ModelLoop(Provider(), executor, TOOLS).run_case(CASE, "probe", "mock")
    return {"arguments_parse_error": parsed.tool_calls[0].arguments_parse_error,
            "validation_errors": record.response_raw["validation_errors"],
            "dispatched": len(executor.calls),
            "argument_is_nan": bool(executor.calls) and math.isnan(executor.calls[0]["arguments"]["temperature"])}


def nonfinite_l1():
    case = {"case_id": "P01", "level": "L1", "category": "positive", "action": "tools_call",
            "service": "auto", "tool": "service.setTemp", "arguments": {"temperature": float("nan")},
            "expected_source": "synthetic review probe", "assertions": [{"type": "field_equals", "path": "success", "value": True}]}
    validate_config(case, "case")
    return {"config_accepted": True, "argv": command_for_case(case)}


def lost_decision(mode):
    clock = [0.0]

    class Provider:
        def chat(self, *args, **kwargs):
            if mode == "deadline":
                clock[0] = 2.0
            return response('{"temperature": 22}', "length" if mode == "length" else "tool_calls")

    executor = Executor()
    record = ModelLoop(Provider(), executor, TOOLS, clock=lambda: clock[0]).run_case(
        CASE, "probe", "mock", timeout_seconds=1)
    judge_record(CASE, record)
    decisions = [decision for event in record.events if event["kind"] == "model_response"
                 for decision in event["decisions"]]
    return {"mode": mode, "observed_decisions": len(decisions),
            "judged_calls": len(record.response_raw["tool_calls"]), "dispatched": len(executor.calls),
            "verdict": record.verdict, "reason": record.verdict_reason,
            "expected_verdict": "fail", "record": record.to_dict()}


def verify_previous_fixes():
    path = ROOT / "tests/results/remediation-2026-10-19/verify_review_fixes.py"
    spec = importlib.util.spec_from_file_location("previous_fix_verification", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.HERE = HERE
    module.main()


def main():
    verify_previous_fixes()
    probes = {"C01-L2-nonfinite": nonfinite_dispatch(), "C01-L1-nonfinite": nonfinite_l1(),
              "C02-deadline-decision": lost_decision("deadline"), "C02-length-decision": lost_decision("length")}
    result = {"source_type": "synthetic", "real_device_or_api": False, "probes": probes,
              "engine_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in sorted((ROOT / "src/mcp_eval").rglob("*.py"))}}
    path = HERE / "probe-results.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"evidence": str(path), "observations": {
        key: {k: v for k, v in value.items() if k != "record"} for key, value in probes.items()}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
