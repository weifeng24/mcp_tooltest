"""2026-10-16 审查反例：不访问真实 API 或设备。"""
from __future__ import annotations

import pytest

from mcp_eval.config import ConfigError, validate_config
from mcp_eval.judge import judge_record
from mcp_eval.records import EvalRecord


def model_case(assertions):
    return {"case_id": "M01", "level": "L2", "category": "positive",
            "service": "auto", "action": "model_task", "task": "调到22度",
            "assertions": assertions, "expected_source": "review contract"}


def observed(response, *, status="completed", category=None, complete=True):
    record = EvalRecord(run_id="test", case_id="M01", channel="replay",
                        action="model_task", service="auto", response_raw=response,
                        execution_status=status, error_category=category)
    record.trace_complete = complete
    return record


def test_provider_error_does_not_pass_no_call():
    case = model_case([{"type": "no_tool_call"}])
    rec = observed({"tool_calls": [], "stopped_reason": "provider_error"},
                   status="error", category="provider_error", complete=False)
    assert judge_record(case, rec).verdict == "unassessed"


def test_missing_trace_is_not_zero_calls():
    case = model_case([{"type": "no_tool_call"}])
    assert judge_record(case, observed(None, complete=False)).verdict == "unassessed"


def test_limit_reached_cannot_pass_task():
    case = model_case([{"type": "model_selects_tool", "name_contains": "setTemp"}])
    rec = observed({"tool_calls": [{"name": "setTemp"}], "stopped_reason": "max_rounds",
                    "final_answer": None})
    assert judge_record(case, rec).verdict == "fail"


def test_rejected_argument_attempt_is_not_successful_selection():
    case = model_case([{"type": "model_selects_tool", "name_contains": "setTemp"}])
    rec = observed({"tool_calls": [{"name": "setTemp", "executed": False,
                                   "result": {"isError": True}}],
                    "stopped_reason": "final_answer", "final_answer": "完成"})
    assert judge_record(case, rec).verdict == "fail"


def test_assertion_missing_selector_is_configuration_error():
    with pytest.raises(ConfigError):
        validate_config(model_case([{"type": "model_selects_tool"}]), "case")


def test_known_forbidden_decision_wins_over_later_provider_error():
    case = model_case([{"type": "no_tool_call"}])
    rec = observed({"tool_calls": [{"name": "setTemp", "executed": True}]},
                   status="error", category="provider_error", complete=False)
    assert judge_record(case, rec).verdict == "fail"


def test_timeout_without_complete_tracking_is_unknown():
    case = model_case([{"type": "no_tool_call"}])
    rec = observed(None, status="timeout", category="timeout", complete=False)
    assert judge_record(case, rec).verdict == "unassessed"


def test_null_protocol_error_is_not_valid_expected_failure():
    case = model_case([{"type": "error_expected"}])
    rec = observed({"error": None})
    rec.action = "tools_call"
    assert judge_record(case, rec).verdict == "unassessed"


@pytest.mark.parametrize("business_success,expected", [(False, "fail"), (True, "pass")])
def test_tool_call_checks_configured_business_result(business_success, expected):
    case = model_case([{"type": "tool_call_matches", "name": "service.setTemp",
                        "arguments": {"temperature": 22}, "result_path": "structuredContent.success",
                        "result_value": True}])
    rec = observed({"tool_calls": [{"name": "service.setTemp", "arguments": {"temperature": 22},
                                    "executed": True, "execution_status": "completed",
                                    "result": {"isError": False, "structuredContent": {"success": business_success}}}],
                    "stopped_reason": "final_answer", "final_answer": "已设置22度"})
    assert judge_record(case, rec).verdict == expected
