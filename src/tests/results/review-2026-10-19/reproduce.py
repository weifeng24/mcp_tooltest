"""当前工作树的离线审查反例；不连接设备或模型，不修改产品源码。"""
from __future__ import annotations

import copy
import hashlib
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from mcp_eval.config import load_config
from mcp_eval.device import AdbResult, DeviceChannel
from mcp_eval.judge import judge_record
from mcp_eval.model_loop import ModelLoop
from mcp_eval.providers.openai_compat import OpenAICompatProvider
from mcp_eval.records import EvalRecord, read_jsonl
from mcp_eval.runner import _execute_item, run_evaluation

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def record(case, response):
    return EvalRecord(
        run_id="probe", case_id=case["case_id"], channel="device", action="tools_call",
        service=case["service"], tool=case["tool"], arguments=case.get("arguments", {}),
        execution_status="completed", trace_complete=True, source_type="synthetic",
        request_raw={"id": 1, "method": "tools/call"}, response_raw=response,
    )


def success(case, *, error=False):
    content = {"success": True} if case["tool"].endswith("setTemp") else {"temperature": 22}
    return {"jsonrpc": "2.0", "id": 1, "result": {"isError": error, "structuredContent": content}}


def judge_error_flags(case, error_at):
    class Channel:
        name = "device"

        def execute_case(self, current, run_id, timeout):
            wrong = current["tool"].endswith(error_at)
            reply = success(current, error=wrong)
            # 使用真实设备解析器验证错误标志不会被解析阶段丢弃。
            channel = DeviceChannel(lambda *args: AdbResult(0, json.dumps(reply), "", 1))
            result = channel.execute_case(current, run_id, timeout)
            result.source_type = "synthetic"
            return result

    result = _execute_item({}, case, {"run_id": "probe"}, Channel(), [], {})
    judge_record(case, result)
    return {"verdict": result.verdict, "reason": result.verdict_reason,
            "primary": result.response_raw, "postconditions": result.provenance["postconditions"]}


def interrupted_after_primary(case, exception_type):
    calls = []

    class Channel:
        name = "device"
        source_type = "synthetic"

        def execute_case(self, current, run_id, timeout):
            calls.append(current["tool"])
            if len(calls) == 2:
                raise exception_type("synthetic interruption during readback")
            return record(current, success(current))

    with tempfile.TemporaryDirectory(prefix="probe-", dir=HERE) as directory:
        root = Path(directory)
        inputs = {
            "case.json": case,
            "server.json": {"server_id": "probe", "baseline_tree": "/not-used",
                            "baseline_commit": "abcdef0", "device_serial": "synthetic", "services": ["auto"]},
            "run.json": {"run_id": "probe", "channel": "device", "server_ref": "server.json",
                         "case_glob": "case.json", "output_dir": "results"},
        }
        for name, value in inputs.items():
            (root / name).write_text(json.dumps(value), encoding="utf-8")
        with patch("mcp_eval.runner.build_channel", return_value=Channel()):
            outcome = run_evaluation("run.json", root)
        stored = read_jsonl(outcome["results"])[0]
        return {"calls_before_failure": calls, "interrupted": outcome["interrupted"],
                "executed_counter": outcome["executed"], "stored_record": stored}


def malformed_no_call():
    class Provider:
        def chat(self, *args, **kwargs):
            return OpenAICompatProvider._parse({"choices": [{"finish_reason": "stop", "message": {
                "content": "你好", "tool_calls": {}}}]})

    class Executor:
        channel = "replay"
        source_type = "synthetic"

        def __call__(self, *args, **kwargs):
            raise AssertionError("不应执行工具")

    case = {"case_id": "M03", "service": "auto", "action": "model_task", "task": "你好",
            "assertions": [{"type": "no_tool_call"}]}
    result = ModelLoop(Provider(), Executor(), [{"name": "s.read", "inputSchema": {"type": "object"}}]).run_case(
        case, "probe", "mock")
    judge_record(case, result)
    return {"verdict": result.verdict, "trace_complete": result.trace_complete, "events": result.events}


def numeric_readback(case):
    result = record(case, success(case))
    readback = {**case, "tool": "HvacService.getTemp", "arguments": {}}
    response = success(readback)
    response["result"]["structuredContent"]["temperature"] = 22.0
    result.provenance["postconditions"] = [record(readback, response).to_dict()]
    judge_record(case, result)
    return {"verdict": result.verdict, "reason": result.verdict_reason, "expected": 22, "observed": 22.0}


def late_l1(case):
    clock = [0.0]
    case = copy.deepcopy(case)
    case["timeout_seconds"] = 1
    case["postconditions"] = []

    class Channel:
        name = "device"

        def execute_case(self, current, run_id, timeout):
            clock[0] = 2.0
            return record(current, success(current))

    with patch("mcp_eval.runner.time.monotonic", side_effect=lambda: clock[0]):
        result = _execute_item({}, case, {"run_id": "probe", "timeout_seconds": 1}, Channel(), [], {})
    judge_record(case, result)
    return {"verdict": result.verdict, "execution_status": result.execution_status,
            "latency_ms": result.latency_ms, "budget_ms": 1000}


def main():
    case = load_config(ROOT / "tests/cases/l1/P02_set_temp_valid.json", "case")
    probes = [
        {"id": "C01-primary-error", "expected": "不得pass", "actual": judge_error_flags(case, "setTemp")},
        {"id": "C01-readback-error", "expected": "不得pass", "actual": judge_error_flags(case, "getTemp")},
        {"id": "C02-interrupt", "expected": "保留主调用与部分执行状态", "actual": interrupted_after_primary(case, KeyboardInterrupt)},
        {"id": "C02-oserror", "expected": "保留主调用与后置错误", "actual": interrupted_after_primary(case, OSError)},
        {"id": "C03-numeric", "expected": "pass：22与22.0为相同JSON数值", "actual": numeric_readback(case)},
        {"id": "C04-malformed-calls", "expected": "ProviderError或unassessed", "actual": malformed_no_call()},
        {"id": "C05-late-l1", "expected": "不得pass：任务已经超过截止时间", "actual": late_l1(case)},
    ]
    reproduced = [
        probes[0]["actual"]["verdict"] == "pass",
        probes[1]["actual"]["verdict"] == "pass",
        probes[2]["actual"]["stored_record"]["execution_status"] == "not_run",
        probes[3]["actual"]["stored_record"]["response_raw"] is None,
        probes[4]["actual"]["verdict"] == "fail",
        probes[5]["actual"]["verdict"] == "pass",
        probes[6]["actual"]["verdict"] == "pass",
    ]
    for probe, hit in zip(probes, reproduced):
        probe["issue_reproduced"] = hit
    evidence = {"source_type": "synthetic", "real_device_or_api": False,
                "engine_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in sorted((ROOT / "src/mcp_eval").rglob("*.py"))},
                "probes": probes, "reproduced": sum(reproduced), "total": len(probes)}
    (HERE / "probe-results.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"reproduced": sum(reproduced), "total": len(probes),
                      "evidence": str(HERE / "probe-results.json")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
