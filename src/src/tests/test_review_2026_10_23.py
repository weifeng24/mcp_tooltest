"""10-23复审整改回归：非有限参数不得下发；已观察的禁止调用不得漏判。"""
from __future__ import annotations

import json
import math

import pytest

from mcp_eval.config import ConfigError, validate_config
from mcp_eval.device import command_for_case
from mcp_eval.judge import judge_record
from mcp_eval.model_loop import ModelLoop
from mcp_eval.providers.base import ProviderResponse
from mcp_eval.providers.openai_compat import OpenAICompatProvider
from mcp_eval.records import EvalRecord

TOOLS = [{"name": "service.setTemp", "inputSchema": {
    "type": "object", "properties": {"temperature": {"type": "number", "minimum": 16, "maximum": 30}},
    "required": ["temperature"], "additionalProperties": False}}]
NO_CALL_CASE = {"case_id": "M03", "action": "model_task", "service": "auto",
                "task": "不要调用任何工具，仅回答你好",
                "assertions": [{"type": "no_tool_call"}]}

VALID_L1_CASE = {"case_id": "P01", "level": "L1", "category": "positive", "service": "auto",
                 "action": "tools_call", "tool": "service.setTemp", "arguments": {"temperature": 22},
                 "assertions": [{"type": "field_equals", "path": "success", "value": True}],
                 "expected_source": "unit test"}


def response_with_call(arguments, finish_reason="tool_calls"):
    return OpenAICompatProvider._parse({"choices": [{"finish_reason": finish_reason, "message": {
        "content": None, "tool_calls": [{"id": "call-1", "type": "function", "function": {
            "name": "service_setTemp", "arguments": arguments}}]}}]})


class CountingExecutor:
    channel = "replay"
    source_type = "synthetic"

    def __init__(self):
        self.calls = []

    def __call__(self, name, arguments, *, timeout):
        self.calls.append({"name": name, "arguments": arguments})
        return EvalRecord(run_id="r", case_id="M03", channel="replay", action="tools_call",
                          service="auto", tool=name, arguments=arguments, trace_complete=True,
                          execution_status="completed", source_type="synthetic",
                          response_raw={"jsonrpc": "2.0", "id": 1, "result": {"isError": False}})


@pytest.mark.parametrize("raw", [
    '{"temperature": NaN}',
    '{"temperature": Infinity}',
    '{"temperature": -Infinity}',
    '{"temperature": 1e309}',
    '{"temperature": 22, "zones": [NaN]}',
])
def test_nonfinite_model_arguments_are_parse_errors(raw):
    parsed = response_with_call(raw)
    assert parsed.tool_calls[0].arguments_parse_error is not None


def test_nonfinite_model_arguments_are_not_dispatched():
    class Provider:
        rounds = 0

        def chat(self, *args, **kwargs):
            self.rounds += 1
            if self.rounds == 1:
                return response_with_call('{"temperature": NaN}')
            return ProviderResponse(content="完成", finish_reason="stop")

    executor = CountingExecutor()
    record = ModelLoop(Provider(), executor, TOOLS).run_case(NO_CALL_CASE, "r", "mock")
    assert executor.calls == []
    assert record.response_raw["validation_errors"] >= 1


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, [22, math.nan], {"inner": math.inf}])
def test_nonfinite_case_arguments_rejected(value):
    case = {**VALID_L1_CASE, "arguments": {"temperature": value}}
    with pytest.raises(ConfigError, match="非有限"):
        validate_config(case, "case")


@pytest.mark.parametrize("value", [22, 16, 30, 22.5, 0, -273.15, [22, 22.0], {"inner": 3}])
def test_finite_case_arguments_accepted(value):
    assert validate_config({**VALID_L1_CASE, "arguments": {"temperature": value}}, "case")


def test_command_for_case_rejects_nonfinite_direct_arguments():
    case = {**VALID_L1_CASE, "arguments": {"temperature": math.nan}}
    with pytest.raises(ValueError, match="非有限|NaN"):
        command_for_case(case)


@pytest.mark.parametrize("mode", ["deadline", "length"])
def test_observed_forbidden_decision_is_fail_on_abnormal_finish(mode):
    clock = [0.0]

    class Provider:
        def chat(self, *args, **kwargs):
            if mode == "deadline":
                clock[0] = 2.0
            return response_with_call('{"temperature": 22}',
                                      "length" if mode == "length" else "tool_calls")

    executor = CountingExecutor()
    record = ModelLoop(Provider(), executor, TOOLS, clock=lambda: clock[0]).run_case(
        NO_CALL_CASE, "r", "mock", timeout_seconds=1)
    assert executor.calls == []
    assert judge_record(NO_CALL_CASE, record).verdict == "fail"


def test_provider_error_without_decision_remains_unassessed():
    class Provider:
        def chat(self, *args, **kwargs):
            from mcp_eval.providers.base import ProviderError
            raise ProviderError("HTTP 500")

    record = ModelLoop(Provider(), CountingExecutor(), TOOLS).run_case(NO_CALL_CASE, "r", "mock")
    assert judge_record(NO_CALL_CASE, record).verdict == "unassessed"


def test_observed_decision_evidence_survives_record_serialization():
    class Provider:
        def chat(self, *args, **kwargs):
            return response_with_call('{"temperature": 22}', "length")

    record = ModelLoop(Provider(), CountingExecutor(), TOOLS).run_case(NO_CALL_CASE, "r", "mock")
    restored = EvalRecord.from_dict(json.loads(json.dumps(record.to_dict(), ensure_ascii=False)))
    assert judge_record(NO_CALL_CASE, restored).verdict == "fail"
