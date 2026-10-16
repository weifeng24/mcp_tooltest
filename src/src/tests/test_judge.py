"""判定器的单元测试。"""
from __future__ import annotations

from mcp_eval.judge import judge_record
from mcp_eval.records import EvalRecord

CASE_POSITIVE = {
    "case_id": "P02",
    "level": "L1",
    "category": "positive",
    "service": "auto",
    "action": "tools_call",
    "tool": "HvacService.setTemp",
    "arguments": {"temperature": 22},
    "assertions": [{"type": "field_equals", "path": "success", "value": True}],
}

CASE_NEGATIVE = {
    "case_id": "N01",
    "level": "L1",
    "category": "negative",
    "service": "MCPVehicleService",
    "action": "tools_call",
    "tool": "MCPVehicleService.noSuchTool",
    "arguments": {},
    "assertions": [{"type": "error_expected"}],
}

CASE_L2_NO_CALL = {
    "case_id": "M03",
    "level": "L2",
    "category": "negative",
    "service": "auto",
    "action": "model_task",
    "task": "写一首诗",
    "assertions": [{"type": "no_tool_call"}],
}


def make_record(**overrides) -> EvalRecord:
    base = dict(
        run_id="r1",
        case_id="P02",
        channel="device",
        action="tools_call",
        service="auto",
        tool="HvacService.setTemp",
        arguments={"temperature": 22},
        execution_status="completed",
        response_raw={"jsonrpc": "2.0", "result": {"success": True}, "id": 1},
    )
    return EvalRecord(**{**base, **overrides})


# ---------- L1 正向 ----------


def test_positive_pass_when_assertion_met():
    record = judge_record(CASE_POSITIVE, make_record())
    assert record.verdict == "pass"


def test_positive_fail_when_field_mismatch():
    record = judge_record(
        CASE_POSITIVE, make_record(response_raw={"result": {"success": False}})
    )
    assert record.verdict == "fail"
    assert "success" in record.verdict_reason


def test_field_equals_finds_field_under_result_wrapper():
    # path "success" 应能命中 result.success（响应包装形态）
    record = judge_record(CASE_POSITIVE, make_record())
    assert record.verdict == "pass"


# ---------- L1 负面（error_expected） ----------


def test_error_expected_pass_on_protocol_error():
    record = judge_record(
        CASE_NEGATIVE,
        make_record(case_id="N01", response_raw={"jsonrpc": "2.0", "error": {"code": -32602}, "id": 1}),
    )
    assert record.verdict == "pass"


def test_error_expected_pass_on_is_error_result():
    record = judge_record(
        CASE_NEGATIVE,
        make_record(case_id="N01", response_raw={"result": {"isError": True, "content": []}}),
    )
    assert record.verdict == "pass"


def test_error_expected_fail_when_call_succeeds():
    """负面用例却成功了——这是有效评测发现，判 fail。"""
    record = judge_record(CASE_NEGATIVE, make_record(case_id="N01"))
    assert record.verdict == "fail"
    assert "预期错误未出现" in record.verdict_reason


def test_infra_error_never_satisfies_error_expected():
    """adb/解析失败是基础设施问题，未观察到工具行为，不能算预期错误。"""
    record = judge_record(
        CASE_NEGATIVE,
        make_record(case_id="N01", execution_status="error",
                    error_category="parse_failed", response_raw=None),
    )
    assert record.verdict == "unassessed"
    assert "基础设施错误" in record.verdict_reason


# ---------- 状态映射 ----------


def test_blocked_is_unassessed():
    record = judge_record(
        CASE_POSITIVE,
        make_record(execution_status="blocked", error_category="no_recording", response_raw=None),
    )
    assert record.verdict == "unassessed"


def test_timeout_positive_is_fail():
    record = judge_record(
        CASE_POSITIVE,
        make_record(execution_status="timeout", error_category="timeout", response_raw=None),
    )
    assert record.verdict == "fail"


# ---------- L2 断言 ----------


def test_no_tool_call_pass():
    record = judge_record(
        CASE_L2_NO_CALL,
        make_record(case_id="M03", action="model_task",
                    response_raw={"tool_calls": [], "final_answer": "好的……"}),
    )
    assert record.verdict == "pass"


def test_no_tool_call_violation_is_fail():
    record = judge_record(
        CASE_L2_NO_CALL,
        make_record(case_id="M03", action="model_task",
                    response_raw={"tool_calls": [{"name": "16777217.setTemp", "arguments": {"temperature": 25}}]}),
    )
    assert record.verdict == "fail"
    assert "负面控制被违反" in record.verdict_reason


def test_model_selects_tool_by_substring():
    case = {
        **CASE_L2_NO_CALL,
        "category": "positive",
        "assertions": [
            {"type": "model_selects_tool", "name_contains": "setTemp"},
            {"type": "max_rounds", "value": 3},
        ],
    }
    record = judge_record(
        case,
        make_record(case_id="M01", action="model_task",
                    response_raw={
                        "tool_calls": [{"name": "16777217.setTemp", "arguments": {"temperature": 22}}],
                        "rounds": 1,
                    }),
    )
    assert record.verdict == "pass"


def test_max_rounds_exceeded_fails():
    case = {**CASE_L2_NO_CALL, "category": "positive",
            "assertions": [{"type": "max_rounds", "value": 2}]}
    record = judge_record(
        case,
        make_record(action="model_task", response_raw={"tool_calls": [], "rounds": 5}),
    )
    assert record.verdict == "fail"
    assert "轮数" in record.verdict_reason


# ---------- manual_review 与防御 ----------


def test_manual_review_forces_unassessed_after_auto_pass():
    case = {**CASE_L2_NO_CALL, "assertions": [{"type": "manual_review"}]}
    record = judge_record(case, make_record(action="model_task", response_raw={}))
    assert record.verdict == "unassessed"
    assert "人工复核" in record.verdict_reason


def test_unknown_assertion_type_fails_closed():
    case = {**CASE_POSITIVE, "assertions": [{"type": "not_a_real_assertion"}]}
    record = judge_record(case, make_record())
    assert record.verdict == "fail"
    assert "未知断言类型" in record.verdict_reason
