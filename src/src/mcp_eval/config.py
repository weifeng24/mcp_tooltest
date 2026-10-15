"""评测配置的加载与校验。

配置分四类：server（被测服务与环境）、model（模型接入）、case（评测用例）、
run（一次运行的编排）。所有配置为 JSON，加载时按 schema 校验，
非法配置在加载期报错并指明字段，避免运行到一半才失败。
"""
from __future__ import annotations

import json
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
            "description": "服务名；auto 表示按工具名经 svcmap/tools_list 解析",
        },
        "action": {"enum": CASE_ACTIONS},
        "tool": {"type": "string", "minLength": 1},
        "arguments": {"type": "object"},
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
        "notes": {"type": "string"},
    },
    "additionalProperties": False,
}

RUN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["run_id", "channel", "server_ref", "case_glob", "output_dir"],
    "properties": {
        "run_id": {"type": "string", "minLength": 1},
        "channel": {"enum": ["device", "replay"]},
        "server_ref": {"type": "string", "minLength": 1},
        "model_refs": {"type": "array", "items": {"type": "string", "minLength": 1}},
        "case_glob": {"type": "string", "minLength": 1},
        "repeat": {"type": "integer", "minimum": 1},
        "timeout_seconds": {"type": "integer", "minimum": 1},
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
    return data


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
    except json.JSONDecodeError as exc:
        raise ConfigError(f"{p}: JSON 解析失败: {exc}") from exc
    return validate_config(data, kind, source=str(p))
