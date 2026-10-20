"""独立判定器：只有可观察、完整且符合用例契约的证据才能通过。"""
from __future__ import annotations

import json
import math
import re
from typing import Any

import jsonschema

from .config import ConfigError, validate_assertions
from .records import EvalRecord


def _set(record: EvalRecord, verdict: str, reason: str) -> EvalRecord:
    record.verdict, record.verdict_reason = verdict, reason
    return record


def resolve_path(data: Any, path: str) -> tuple[bool, Any]:
    """路径相对响应根节点；保留旧用例相对 result 的写法。"""
    for candidate in (path, "result." + path):
        current = data
        for part in candidate.split("."):
            if isinstance(current, dict) and part in current:
                current = current[part]
            elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
                current = current[int(part)]
            else:
                break
        else:
            return True, current
    return False, None


def json_equal(left: Any, right: Any) -> bool:
    """比较JSON值而非序列化文本；布尔与数值分开，非有限数不相等。"""
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    if type(left) in (int, float) and type(right) in (int, float):
        return (not isinstance(left, float) or math.isfinite(left)) and (
            not isinstance(right, float) or math.isfinite(right)) and left == right
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(json_equal(left[key], right[key]) for key in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(json_equal(a, b) for a, b in zip(left, right))
    return left == right


def response_result(response: Any) -> dict[str, Any] | None:
    if not isinstance(response, dict) or "error" in response:
        return None
    result = response.get("result")
    return result if isinstance(result, dict) else None


def response_success(response: Any) -> tuple[bool | None, str]:
    """工具成功的前置条件；业务字段断言在此前置条件之后执行。"""
    if not isinstance(response, dict):
        return None, "响应对象缺失"
    if "error" in response:
        error = response["error"]
        if ("result" in response or not isinstance(error, dict) or type(error.get("code")) is not int
                or not isinstance(error.get("message"), str)):
            return None, "协议错误响应不完整或冲突"
        return False, "工具返回协议错误"
    result = response_result(response)
    if result is None:
        return None, "工具结果对象缺失"
    flag = result.get("isError", False)
    if type(flag) is not bool:
        return None, "isError必须为布尔值"
    if flag or "error" in result:
        return False, "工具返回错误状态"
    for value in (result, result.get("structuredContent")):
        if isinstance(value, dict) and "success" in value:
            if type(value["success"]) is not bool:
                return None, "success必须为布尔值"
            if value["success"] is False:
                return False, "业务success为false"
    return True, ""


def tool_succeeded(call: dict[str, Any]) -> bool:
    return (call.get("executed") is True and call.get("execution_status") == "completed"
            and response_success({"result": call.get("result")})[0] is True)


def judge_record(case: dict[str, Any], record: EvalRecord) -> EvalRecord:
    try:
        validate_assertions(case["assertions"])
    except (ConfigError, KeyError) as exc:
        return _set(record, "unassessed", f"判据错误: {exc}")
    response = record.response_raw
    calls = response.get("tool_calls") if isinstance(response, dict) else None
    # 已保存的调用决策能证明禁止调用被违反，即使后续 API 失败。
    if any(a["type"] == "no_tool_call" for a in case["assertions"]) and isinstance(calls, list) and calls:
        return _set(record, "fail", "负面控制被违反：已观察到工具调用决策")
    if record.execution_status in ("blocked", "not_run", "error") or not record.trace_complete:
        return _set(record, "unassessed", f"执行或证据不完整: {record.error_category or record.execution_status}")
    if record.execution_status == "timeout":
        return _set(record, "fail", "完整跟踪确认任务未在时限内完成")
    if not isinstance(response, dict):
        return _set(record, "unassessed", "响应证据缺失")
    if record.action == "tools_call" and not any(a["type"] == "error_expected" for a in case["assertions"]):
        success, reason = response_success(response)
        if success is not True:
            return _set(record, "fail" if success is False else "unassessed", reason)
    if record.action == "model_task":
        if response.get("stopped_reason") in ("max_rounds", "max_tool_calls"):
            return _set(record, "fail", "达到调用上限但任务未完成")
        if not isinstance(calls, list) or response.get("stopped_reason") != "final_answer":
            return _set(record, "unassessed", "模型调用轨迹或终止原因缺失")
        if not isinstance(response.get("final_answer"), str) or not response["final_answer"].strip():
            return _set(record, "unassessed", "最终回答缺失")
    failures, unknown = [], []
    for assertion in case["assertions"]:
        try:
            outcome, reason = _evaluate(assertion, record)
        except (TypeError, ValueError, AttributeError, KeyError) as exc:
            outcome, reason = None, f"判定输入格式错误: {type(exc).__name__}"
        if outcome is False:
            failures.append(reason)
        elif outcome is None:
            unknown.append(reason)
    # 后置状态由执行器独立回读，不能用模型说“已完成”替代。
    verifications = record.provenance.get("postconditions", [])
    for index, expected in enumerate(case.get("postconditions", [])):
        checked = verifications[index] if isinstance(verifications, list) and index < len(verifications) else None
        if (not isinstance(checked, dict) or checked.get("trace_complete") is not True
                or checked.get("execution_status") != "completed"):
            unknown.append("后置状态回读证据不足")
            continue
        if (checked.get("action") != "tools_call" or checked.get("tool") != expected["tool"]
                or not json_equal(checked.get("arguments"), expected["arguments"])):
            unknown.append("后置回读身份与预期工具或参数不符")
            continue
        success, reason = response_success(checked.get("response_raw"))
        if success is not True:
            (failures if success is False else unknown).append("后置回读：" + reason)
            continue
        found, value = resolve_path(checked.get("response_raw"), expected["path"])
        if not found or not json_equal(value, expected["value"]):
            failures.append(f"后置状态 {expected['path']} 不符合预期")
    if failures:
        return _set(record, "fail", "；".join(failures))
    if unknown:
        return _set(record, "unassessed", "；".join(unknown))
    return _set(record, "pass", "全部断言及后置条件通过")


def _evaluate(assertion: dict[str, Any], record: EvalRecord) -> tuple[bool | None, str]:
    kind, response = assertion["type"], record.response_raw
    result = response_result(response)
    if kind == "manual_review":
        return None, "需人工复核"
    if kind == "field_equals":
        found, value = resolve_path(response, assertion["path"])
        return found and json_equal(value, assertion["value"]), f"字段 {assertion['path']} 不符合预期"
    if kind == "error_expected":
        return _expected_error(assertion, response)
    if kind in ("model_selects_tool", "tool_call_matches", "no_tool_call", "max_rounds", "final_answer_contains"):
        calls = response.get("tool_calls")
        if not isinstance(calls, list) or any(not isinstance(c, dict) for c in calls):
            return None, "缺少有效调用轨迹"
        if kind == "no_tool_call":
            return not calls, "存在非预期工具调用"
        if kind == "max_rounds":
            rounds = response.get("rounds")
            return (rounds <= assertion["value"], "模型轮数超过上限") if type(rounds) is int else (None, "轮数未知")
        if kind == "final_answer_contains":
            return assertion["text"] in response.get("final_answer", ""), "最终回答未包含所需事实"
        if kind == "tool_call_matches":
            matched = [c for c in calls if c.get("name") == assertion["name"]
                       and json_equal(c.get("arguments"), assertion["arguments"]) and tool_succeeded(c)]
            if "result_path" in assertion:
                matched = [c for c in matched if resolve_path(c["result"], assertion["result_path"])[0]
                           and json_equal(resolve_path(c["result"], assertion["result_path"])[1], assertion["result_value"])]
        else:
            matched = [c for c in calls if assertion["name_contains"] in str(c.get("name", "")) and tool_succeeded(c)]
        return bool(matched), "没有已执行且成功的匹配工具/参数"
    if result is None:
        return None, "缺少有效结果对象"
    if kind == "list_non_empty":
        key = {"tools_list": "tools", "resources_list": "resources", "resources_read": "contents"}.get(record.action)
        if not key:
            return None, "列表断言与操作不匹配"
        value = result.get(key)
        return isinstance(value, list) and bool(value), f"{key} 为空或格式错误"
    tools = result.get("tools")
    if not isinstance(tools, list) or not tools or any(not isinstance(t, dict) for t in tools):
        return False, "工具列表缺失或格式错误"
    if kind == "tools_have_schema":
        for tool in tools:
            if not isinstance(tool.get("name"), str) or not tool["name"]:
                return False, "工具名称缺失"
            for field in ("inputSchema", "outputSchema"):
                if field == "outputSchema" and field not in tool:
                    continue  # MCP 的 outputSchema 是可选项。
                schema = tool.get(field)
                if not isinstance(schema, dict):
                    return False, f"{field} 不是对象"
                try:
                    jsonschema.validators.validator_for(schema).check_schema(schema)
                except jsonschema.SchemaError:
                    return False, f"{field} 非法"
        return True, ""
    if kind == "tool_name_prefixed":
        return all(re.fullmatch(r"[^.\s]+\.[^.\s]+", str(t.get("name", ""))) for t in tools), "工具名前缀格式错误"
    if kind == "list_contains_tool":
        return any(t.get("name") == assertion["name"] for t in tools), "工具列表未找到指定完整名称"
    return None, f"未知断言类型 {kind}"


def _expected_error(assertion: dict[str, Any], response: dict[str, Any]) -> tuple[bool | None, str]:
    if "error" in response:
        error = response["error"]
        if not isinstance(error, dict) or type(error.get("code")) is not int or not isinstance(error.get("message"), str):
            return None, "错误响应格式不完整"
        code, message = error["code"], error["message"]
    else:
        result = response_result(response)
        if result is None:
            return None, "没有有效响应"
        if result.get("isError", False) is not True:
            return False, "预期错误未出现"
        code, message = result.get("statusCode"), json.dumps(result.get("content", []), ensure_ascii=False)
    if "codes" in assertion and code not in assertion["codes"]:
        return False, "错误码不符合预期，不能用其他错误代替"
    if "message_pattern" in assertion and not re.search(assertion["message_pattern"], message):
        return False, "错误原因不符合预期"
    return True, ""
