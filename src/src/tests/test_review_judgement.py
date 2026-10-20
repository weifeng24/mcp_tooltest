"""10-19复审：工具成功条件、JSON数值语义和提供方响应边界。"""
import copy

import pytest

from mcp_eval.judge import json_equal, judge_record
from mcp_eval.model_loop import ModelLoop
from mcp_eval.providers.base import ProviderError
from mcp_eval.providers.openai_compat import OpenAICompatProvider
from mcp_eval.records import EvalRecord


CASE = {"case_id": "P02", "action": "tools_call", "service": "auto", "tool": "s.set",
        "arguments": {"temperature": 22},
        "assertions": [{"type": "field_equals", "path": "structuredContent.success", "value": True}],
        "postconditions": [{"tool": "s.get", "arguments": {}, "path": "structuredContent.temperature", "value": 22}]}


def observed(tool, arguments, content):
    return EvalRecord(run_id="r", case_id="P02", channel="replay", action="tools_call", service="auto",
                      tool=tool, arguments=arguments, execution_status="completed", trace_complete=True,
                      source_type="synthetic", response_raw={"result": {"isError": False, "structuredContent": content}})


def primary():
    record = observed("s.set", {"temperature": 22}, {"success": True})
    record.provenance["postconditions"] = [observed("s.get", {}, {"temperature": 22}).to_dict()]
    return record


@pytest.mark.parametrize("location", ["primary", "readback"])
def test_error_flag_prevents_success_despite_matching_fields(location):
    record = primary()
    response = record.response_raw if location == "primary" else record.provenance["postconditions"][0]["response_raw"]
    response["result"]["isError"] = True
    assert judge_record(CASE, record).verdict == "fail"


@pytest.mark.parametrize("change", [{"tool": "s.other"}, {"arguments": {"zone": 2}}, {"execution_status": "error"}])
def test_readback_requires_expected_call_identity_and_completed_execution(change):
    record = primary()
    record.provenance["postconditions"][0].update(change)
    assert judge_record(CASE, record).verdict == "unassessed"


def test_business_failure_in_readback_cannot_prove_state():
    record = primary()
    record.provenance["postconditions"][0]["response_raw"]["result"]["structuredContent"]["success"] = False
    assert judge_record(CASE, record).verdict == "fail"


def test_protocol_error_remains_valid_for_negative_case():
    record = primary()
    record.response_raw = {"error": {"code": -32602, "message": "out of range"}}
    case = {**CASE, "assertions": [{"type": "error_expected", "codes": [-32602]}], "postconditions": []}
    assert judge_record(case, record).verdict == "pass"


def test_invalid_error_flag_is_unknown_evidence():
    record = primary()
    record.response_raw["result"]["isError"] = "false"
    assert judge_record(CASE, record).verdict == "unassessed"


def test_float_representation_of_temperature_passes_readback():
    record = primary()
    record.provenance["postconditions"][0]["response_raw"]["result"]["structuredContent"]["temperature"] = 22.0
    assert judge_record(CASE, record).verdict == "pass"


@pytest.mark.parametrize("left,right,equal", [
    (22, 22.0, True), ({"a": [22]}, {"a": [22.0]}, True),
    (True, 1, False), ({"a": [False]}, {"a": [0.0]}, False),
    (22, "22", False), ([22], [22, 22], False),
    (float("inf"), float("inf"), False), (float("nan"), float("nan"), False),
])
def test_json_value_equality(left, right, equal):
    assert json_equal(left, right) is equal


@pytest.mark.parametrize("calls", [{}, False, 0, ""])
def test_malformed_tool_calls_is_provider_error(calls):
    with pytest.raises(ProviderError):
        OpenAICompatProvider._parse({"choices": [{"message": {"content": "你好", "tool_calls": calls}}]})


@pytest.mark.parametrize("message", [{"content": "你好"}, {"content": "你好", "tool_calls": None},
                                      {"content": "你好", "tool_calls": []}])
def test_valid_no_call_responses_remain_supported(message):
    assert OpenAICompatProvider._parse({"choices": [{"message": message}]}).tool_calls == []


def test_malformed_zero_calls_cannot_pass_model_negative_control():
    class Provider:
        def chat(self, *args, **kwargs):
            return OpenAICompatProvider._parse({"choices": [{"message": {"content": "你好", "tool_calls": {}}}]})

    class Executor:
        channel = "replay"
        source_type = "synthetic"

        def __call__(self, *args, **kwargs):
            raise AssertionError("非法模型响应不得执行工具")

    case = {"case_id": "M03", "action": "model_task", "service": "auto", "task": "你好",
            "assertions": [{"type": "no_tool_call"}]}
    record = ModelLoop(Provider(), Executor(), [{"name": "s.get", "inputSchema": {"type": "object"}}]).run_case(
        case, "r", "mock")
    assert judge_record(case, record).verdict == "unassessed"
    assert record.error_category == "provider_error"


def test_l2_readback_error_rejected_after_successful_model_call():
    record = primary()
    record.action = "model_task"
    record.response_raw = {"tool_calls": [{"name": "s.set", "arguments": {"temperature": 22}, "executed": True,
                           "execution_status": "completed", "result": {"isError": False}}],
                           "stopped_reason": "final_answer", "final_answer": "已设为22"}
    record.provenance["postconditions"][0]["response_raw"]["result"]["isError"] = True
    case = copy.deepcopy(CASE)
    case["assertions"] = [{"type": "tool_call_matches", "name": "s.set", "arguments": {"temperature": 22}}]
    assert judge_record(case, record).verdict == "fail"
