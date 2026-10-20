"""评测配置的加载与校验。

配置分四类：server（被测服务与环境）、model（模型接入）、case（评测用例）、
run（一次运行的编排）。所有配置为 JSON，加载时按 schema 校验，
非法配置在加载期报错并指明字段，避免运行到一半才失败。
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import jsonschema


class ConfigError(ValueError):
    """配置缺失、格式错误或违反约束时抛出。"""


SERVER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["server_id", "baseline_tree", "baseline_commit", "device_serial", "services"],
    "properties": {
        "server_id": {"type": "string", "minLength": 1},
        "baseline_tree": {"type": "string", "minLength": 1},
        "baseline_commit": {"type": "string", "minLength": 7},
        "device_serial": {"type": "string"},
        "service_bin": {"type": "string", "minLength": 1},
        "dump_dir": {"type": "string", "minLength": 1},
        "services": {
            "type": "array",
            "items": {"type": "string", "minLength": 1},
            "minItems": 1,
        },
        "notes": {"type": "string"},
    },
    "additionalProperties": False,
}

MODEL_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["model_config_id", "provider", "model", "api_key_env"],
    "properties": {
        "model_config_id": {"type": "string", "minLength": 1},
        "provider": {"enum": ["deepseek", "kimi", "openrouter"]},
        "model": {"type": "string", "minLength": 1},
        "base_url": {"type": "string"},
        "api_key_env": {
            "type": "string",
            "minLength": 1,
            "description": "密钥所在环境变量名；配置中不保存密钥明文",
        },
        "generation": {
            "type": "object",
            "properties": {
                "temperature": {"type": "number", "minimum": 0},
                "max_tokens": {"type": "integer", "minimum": 1},
            },
            "additionalProperties": False,
        },
        "notes": {"type": "string"},
    },
    "additionalProperties": False,
}

CASE_ACTIONS = ["tools_list", "tools_call", "resources_list", "resources_read", "model_task"]

ASSERTION_TYPES = [
    "list_non_empty",
    "tools_have_schema",
    "tool_name_prefixed",
    "list_contains_tool",
    "field_equals",
    "error_expected",
    "model_selects_tool",
    "no_tool_call",
    "max_rounds",
    "manual_review",
    "tool_call_matches",
    "final_answer_contains",
]

CASE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["case_id", "level", "category", "service", "action", "assertions", "expected_source"],
    "properties": {
        "case_id": {"type": "string", "pattern": "^[PNME][0-9]{2}$"},
        "level": {"enum": ["L1", "L2"]},
        "category": {"enum": ["positive", "negative", "edge"]},
        "service": {
            "type": "string",
            "minLength": 1,
            "description": "服务元数据；auto 表示使用完整 tool 名路由，不作为车端服务名发送",
        },
        "action": {"enum": CASE_ACTIONS},
        "tool": {"type": "string", "minLength": 1},
        "arguments": {"type": "object"},
        "resource_uri": {"type": "string", "minLength": 1},
        "task": {"type": "string", "minLength": 1},
        "timeout_seconds": {"type": "integer", "minimum": 1},
        "assertions": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["type"],
                "properties": {"type": {"enum": ASSERTION_TYPES}},
            },
        },
        "expected_source": {"type": "string", "minLength": 1},
        "postconditions": {"type": "array", "items": {
            "type": "object", "required": ["tool", "arguments", "path", "value"],
            "properties": {"tool": {"type": "string", "minLength": 1},
                           "arguments": {"type": "object"}, "path": {"type": "string", "minLength": 1},
                           "value": {}}, "additionalProperties": False}},
        "notes": {"type": "string"},
    },
    "additionalProperties": False,
}

RUN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["run_id", "channel", "server_ref", "case_glob", "output_dir"],
    "properties": {
        "run_id": {"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$"},
        "channel": {"enum": ["device", "replay"]},
        "server_ref": {"type": "string", "minLength": 1},
        "model_refs": {"type": "array", "items": {"type": "string", "minLength": 1}},
        "case_glob": {"type": "string", "minLength": 1},
        "recording": {
            "type": "string",
            "description": "replay 通道必填：录制 JSONL 路径（相对交付区根目录）",
        },
        "tools_file": {
            "type": "string",
            "description": "L2 用例所需的 tools/list 采集文件路径",
        },
        "repeat": {"type": "integer", "minimum": 1},
        "timeout_seconds": {"type": "integer", "minimum": 1},
        "max_rounds": {"type": "integer", "minimum": 1},
        "max_tool_calls": {"type": "integer", "minimum": 1},
        "output_dir": {"type": "string", "minLength": 1},
        "notes": {"type": "string"},
    },
    "additionalProperties": False,
}

SCHEMAS: dict[str, dict[str, Any]] = {
    "server": SERVER_SCHEMA,
    "model": MODEL_SCHEMA,
    "case": CASE_SCHEMA,
    "run": RUN_SCHEMA,
}


def validate_config(data: Any, kind: str, source: str = "<memory>") -> Any:
    """按 kind 对应的 schema 校验配置，并检查跨字段约束。

    Raises:
        ConfigError: 类型未知、schema 不满足或跨字段约束不满足。
    """
    schema = SCHEMAS.get(kind)
    if schema is None:
        raise ConfigError(f"{source}: 未知配置类型 {kind!r}，可选 {sorted(SCHEMAS)}")
    try:
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as exc:
        field = ".".join(str(p) for p in exc.absolute_path) or "<root>"
        raise ConfigError(f"{source}: 字段 {field} 不满足约束: {exc.message}") from exc
    if kind == "case":
        _validate_case_cross_fields(data, source)
        validate_assertions(data["assertions"], source)
    if kind == "run":
        _validate_run_cross_fields(data, source)
    return data


def _validate_run_cross_fields(run: dict[str, Any], source: str) -> None:
    if run["channel"] == "replay" and not run.get("recording"):
        raise ConfigError(f"{source}: channel=replay 时必须提供 recording 字段")


def _validate_case_cross_fields(case: dict[str, Any], source: str) -> None:
    action = case["action"]
    if action == "tools_call" and not case.get("tool"):
        raise ConfigError(f"{source}: action=tools_call 时必须提供 tool 字段")
    if action == "model_task" and not case.get("task"):
        raise ConfigError(f"{source}: action=model_task 时必须提供 task 字段")
    if case["level"] == "L2" and action != "model_task":
        raise ConfigError(f"{source}: L2 用例的 action 必须为 model_task")
    if case["level"] == "L1" and action == "model_task":
        raise ConfigError(f"{source}: L1 用例不能使用 model_task")
    if action == "resources_read" and not (case.get("resource_uri") or case.get("tool")):
        raise ConfigError(f"{source}: resources_read 必须提供 resource_uri")


def validate_assertions(assertions: list[dict[str, Any]], source: str = "<memory>") -> None:
    """校验不同断言的必填参数，避免空选择器产生永真匹配。"""
    selectors = {"field_equals": "path", "list_contains_tool": "name",
                 "model_selects_tool": "name_contains", "tool_call_matches": "name",
                 "final_answer_contains": "text"}
    common = {"type"}
    extra = {"field_equals": {"path", "value"}, "list_contains_tool": {"name"},
             "model_selects_tool": {"name_contains"}, "tool_call_matches": {"name", "arguments", "result_path", "result_value"},
             "final_answer_contains": {"text"}, "max_rounds": {"value"},
             "error_expected": {"codes", "message_pattern"}}
    if not isinstance(assertions, list) or not assertions:
        raise ConfigError(f"{source}: assertions 必须为非空列表")
    for index, assertion in enumerate(assertions):
        if not isinstance(assertion, dict) or assertion.get("type") not in ASSERTION_TYPES:
            raise ConfigError(f"{source}: assertions[{index}] 未知断言类型")
        kind = assertion["type"]
        if set(assertion) - common - extra.get(kind, set()):
            raise ConfigError(f"{source}: assertions[{index}] 存在不适用字段")
        selector = selectors.get(kind)
        if selector and (not isinstance(assertion.get(selector), str) or not assertion[selector].strip()):
            raise ConfigError(f"{source}: assertions[{index}].{selector} 不得为空")
        if kind == "field_equals" and "value" not in assertion:
            raise ConfigError(f"{source}: field_equals 缺少 value")
        if kind == "tool_call_matches" and not isinstance(assertion.get("arguments"), dict):
            raise ConfigError(f"{source}: tool_call_matches 缺少 arguments 对象")
        if "result_path" in assertion or "result_value" in assertion:
            if not isinstance(assertion.get("result_path"), str) or not assertion["result_path"].strip() or "result_value" not in assertion:
                raise ConfigError(f"{source}: 业务返回断言需要 result_path 与 result_value")
        if kind == "max_rounds" and (type(assertion.get("value")) is not int or assertion["value"] < 1):
            raise ConfigError(f"{source}: max_rounds.value 必须为正整数")
        if "codes" in assertion and (not isinstance(assertion["codes"], list) or not assertion["codes"]
                                     or any(type(code) is not int for code in assertion["codes"])):
            raise ConfigError(f"{source}: error_expected.codes 必须为非空整数列表")
        if "message_pattern" in assertion:
            pattern = assertion["message_pattern"]
            if not isinstance(pattern, str) or not pattern:
                raise ConfigError(f"{source}: message_pattern 不得为空")
            try:
                re.compile(pattern)
            except re.error as exc:
                raise ConfigError(f"{source}: message_pattern 非法") from exc


def load_config(path: str | Path, kind: str) -> Any:
    """从 JSON 文件加载并校验配置。

    Raises:
        ConfigError: 文件不存在、JSON 解析失败或校验失败。
    """
    p = Path(path)
    if not p.is_file():
        raise ConfigError(f"配置文件不存在: {p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeError, OSError) as exc:
        raise ConfigError(f"{p}: JSON 解析失败: {exc}") from exc
    return validate_config(data, kind, source=str(p))


def validate_tools(tools: Any, source: str = "tools") -> list[dict[str, Any]]:
    """验证完整工具定义；不解析远程 Schema 引用。"""
    if not isinstance(tools, list) or not tools:
        raise ConfigError(f"{source}: 工具列表必须为非空数组")
    names = set()

    def check_refs(value):
        if isinstance(value, dict):
            ref = value.get("$ref")
            if ref is not None and (not isinstance(ref, str) or not ref.startswith("#")):
                raise ConfigError(f"{source}: 不支持外部 $ref，请先提供自包含 Schema")
            for item in value.values():
                check_refs(item)
        elif isinstance(value, list):
            for item in value:
                check_refs(item)

    for tool in tools:
        if not isinstance(tool, dict) or not isinstance(tool.get("name"), str) or not tool["name"].strip():
            raise ConfigError(f"{source}: 工具缺少名称")
        if tool["name"] in names:
            raise ConfigError(f"{source}: 重复工具名 {tool['name']}")
        names.add(tool["name"])
        if not isinstance(tool.get("inputSchema"), dict):
            raise ConfigError(f"{source}: {tool['name']} 缺少 inputSchema")
        for key in ("inputSchema", "outputSchema"):
            if key in tool:
                try:
                    jsonschema.validators.validator_for(tool[key]).check_schema(tool[key])
                except (jsonschema.SchemaError, TypeError, AttributeError) as exc:
                    raise ConfigError(f"{source}: {tool['name']}.{key} 非法") from exc
                check_refs(tool[key])
    return tools
