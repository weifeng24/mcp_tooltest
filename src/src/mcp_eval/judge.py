"""判定器：把执行记录变成 verdict（pass / fail / unassessed）。

判定优先级（与 docs/design.md §5.2 一致）：
1. 已证实的违规（如负面用例中发生了调用）→ fail
2. 跟踪完整但时限内未完成 → fail
3. 全部断言通过 → pass
4. 证据缺失 / 基础设施错误 / 需人工复核 → unassessed

关键区分：adb 失败、输出解析失败等是"基础设施错误"（未观察到工具行为），
不能用来满足 error_expected 断言；只有协议错误响应才算观察到了工具行为。
"""
from __future__ import annotations

from typing import Any

from .records import EvalRecord

# 基础设施错误：工具行为未被观察到，一律 unassessed
INFRA_ERROR_CATEGORIES = {
    "adb_setup_failed",
    "adb_error",
    "parse_failed",
    "exit_nonzero",
}


def judge_record(case: dict[str, Any], record: EvalRecord) -> EvalRecord:
    """按用例断言判定单条记录，就地填写 verdict 并返回。"""
    status = record.execution_status
    if status in ("blocked", "not_run"):
        return _set(record, "unassessed", f"未执行（{record.error_category or status}），证据不足")
    if status == "timeout":
        return _set(record, "fail", "跟踪完整但超时未返回")
    if status == "error" and record.error_category in INFRA_ERROR_CATEGORIES:
        return _set(record, "unassessed", f"基础设施错误（{record.error_category}），未观察到工具行为")

    needs_review = any(a["type"] == "manual_review" for a in case["assertions"])
    failures: list[str] = []
    for assertion in case["assertions"]:
        if assertion["type"] == "manual_review":
            continue
        ok, reason = _eval_assertion(assertion, record)
        if not ok:
            failures.append(reason)
    if failures:
        return _set(record, "fail", "；".join(failures))
    if needs_review:
        return _set(record, "unassessed", "自动断言通过，需人工复核后定判")
    return _set(record, "pass", "全部断言通过")


def _set(record: EvalRecord, verdict: str, reason: str) -> EvalRecord:
    record.verdict = verdict
    record.verdict_reason = reason
    return record


def _eval_assertion(assertion: dict[str, Any], record: EvalRecord) -> tuple[bool, str]:
    atype = assertion["type"]
    handler = _ASSERTION_HANDLERS.get(atype)
    if handler is None:
        return False, f"未知断言类型 {atype}"
    return handler(assertion, record)


def _resolve_path(data: dict[str, Any], path: str) -> tuple[bool, Any]:
    """按 dot 路径取值；根上找不到时尝试 result 下。适配响应包装的两种形态。"""
    for candidate in (path, f"result.{path}"):
        cur: Any = data
        for part in candidate.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                break
        else:
            return True, cur
    return False, None


def _tools(record: EvalRecord) -> list[dict[str, Any]]:
    response = record.response_raw or {}
    tools = response.get("result", {}).get("tools")
    return tools if isinstance(tools, list) else []


def _tool_calls(record: EvalRecord) -> list[dict[str, Any]]:
    response = record.response_raw or {}
    calls = response.get("tool_calls")
    return calls if isinstance(calls, list) else []


def _assert_list_non_empty(_a: dict, record: EvalRecord) -> tuple[bool, str]:
    response = record.response_raw or {}
    result = response.get("result", {})
    for key in ("tools", "resources", "content"):
        value = result.get(key)
        if isinstance(value, list) and value:
            return True, ""
    return False, "响应中 tools/resources/content 均为空或缺失"


def _assert_tools_have_schema(_a: dict, record: EvalRecord) -> tuple[bool, str]:
    tools = _tools(record)
    if not tools:
        return False, "无工具列表可检查 schema"
    bad = [t.get("name", "?") for t in tools if not isinstance(t.get("inputSchema"), dict)]
    if bad:
        return False, f"工具缺少 inputSchema: {bad}"
    return True, ""


def _assert_tool_name_prefixed(_a: dict, record: EvalRecord) -> tuple[bool, str]:
    tools = _tools(record)
    if not tools:
        return False, "无工具列表可检查命名前缀"
    bad = [t.get("name", "?") for t in tools if "." not in str(t.get("name", ""))]
    if bad:
        return False, f"工具名缺少服务前缀（serviceId/serviceName 分隔符）: {bad}"
    return True, ""


def _assert_list_contains_tool(a: dict, record: EvalRecord) -> tuple[bool, str]:
    name = a.get("name", "")
    names = [str(t.get("name", "")) for t in _tools(record)]
    if any(n == name or n.endswith(f".{name}") for n in names):
        return True, ""
    return False, f"工具列表未找到 {name}（实际: {names}）"


def _assert_field_equals(a: dict, record: EvalRecord) -> tuple[bool, str]:
    found, value = _resolve_path(record.response_raw or {}, a.get("path", ""))
    if not found:
        return False, f"响应中未找到字段 {a.get('path')}"
    if value != a.get("value"):
        return False, f"字段 {a.get('path')} 期望 {a.get('value')!r}，实际 {value!r}"
    return True, ""


def _assert_error_expected(_a: dict, record: EvalRecord) -> tuple[bool, str]:
    response = record.response_raw or {}
    if "error" in response:
        return True, ""
    is_error = response.get("result", {}).get("isError")
    if is_error:
        return True, ""
    return False, "预期错误未出现（实际成功或无错误标记）——作为评测发现记录"


def _assert_model_selects_tool(a: dict, record: EvalRecord) -> tuple[bool, str]:
    needle = a.get("name_contains", "")
    names = [str(c.get("name", "")) for c in _tool_calls(record)]
    if any(needle in n for n in names):
        return True, ""
    return False, f"模型未选择含 {needle} 的工具（实际调用: {names}）"


def _assert_no_tool_call(_a: dict, record: EvalRecord) -> tuple[bool, str]:
    calls = _tool_calls(record)
    if not calls:
        return True, ""
    names = [str(c.get("name", "")) for c in calls]
    return False, f"负面控制被违反：发生了工具调用 {names}"


def _assert_max_rounds(a: dict, record: EvalRecord) -> tuple[bool, str]:
    limit = a.get("value", 0)
    response = record.response_raw or {}
    rounds = response.get("rounds", len(_tool_calls(record)))
    if rounds <= limit:
        return True, ""
    return False, f"调用轮数 {rounds} 超过上限 {limit}"


_ASSERTION_HANDLERS = {
    "list_non_empty": _assert_list_non_empty,
    "tools_have_schema": _assert_tools_have_schema,
    "tool_name_prefixed": _assert_tool_name_prefixed,
    "list_contains_tool": _assert_list_contains_tool,
    "field_equals": _assert_field_equals,
    "error_expected": _assert_error_expected,
    "model_selects_tool": _assert_model_selects_tool,
    "no_tool_call": _assert_no_tool_call,
    "max_rounds": _assert_max_rounds,
}
