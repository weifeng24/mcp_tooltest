"""配置加载与校验的单元测试。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from mcp_eval.config import ConfigError, load_config, validate_config

DELIVERY_ROOT = Path(__file__).resolve().parents[2]
CONFIGS_DIR = DELIVERY_ROOT / "configs"
CASES_DIR = DELIVERY_ROOT / "tests" / "cases"

VALID_SERVER = {
    "server_id": "s1",
    "baseline_tree": "/data/tree",
    "baseline_commit": "f152ba8",
    "device_serial": "",
    "services": ["MCPVehicleService"],
}

VALID_CASE = {
    "case_id": "P01",
    "level": "L1",
    "category": "positive",
    "service": "MCPVehicleService",
    "action": "tools_list",
    "assertions": [{"type": "list_non_empty"}],
    "expected_source": "MCP_Agent.md §9.3",
}


def test_example_configs_all_load():
    """configs/ 下全部示例配置必须能通过各自类型的校验。"""
    kind_by_dir = {"servers": "server", "models": "model", "runs": "run"}
    files = sorted(CONFIGS_DIR.rglob("*.json"))
    assert files, "configs/ 下应至少有一个示例配置"
    for f in files:
        kind = kind_by_dir[f.parent.name]
        load_config(f, kind)


def test_example_cases_all_load():
    """tests/cases/ 下全部用例必须能通过 case 校验。"""
    files = sorted(CASES_DIR.rglob("*.json"))
    assert files, "tests/cases/ 下应至少有一个用例"
    for f in files:
        load_config(f, "case")


def test_valid_server_passes():
    assert validate_config(dict(VALID_SERVER), "server")["server_id"] == "s1"


def test_missing_required_field_reports_field_name():
    data = dict(VALID_SERVER)
    del data["baseline_tree"]
    with pytest.raises(ConfigError, match="baseline_tree"):
        validate_config(data, "server")


def test_invalid_enum_rejected():
    data = {
        "run_id": "r1",
        "channel": "usb",
        "server_ref": "x.json",
        "case_glob": "*.json",
        "output_dir": "out",
    }
    with pytest.raises(ConfigError, match="channel"):
        validate_config(data, "run")


def test_additional_property_rejected():
    data = dict(VALID_SERVER, unexpected="x")
    with pytest.raises(ConfigError):
        validate_config(data, "server")


def test_unknown_kind_rejected():
    with pytest.raises(ConfigError, match="未知配置类型"):
        validate_config({}, "widget")


def test_case_id_pattern_enforced():
    data = dict(VALID_CASE, case_id="X99")
    with pytest.raises(ConfigError):
        validate_config(data, "case")


def test_tools_call_requires_tool():
    data = dict(VALID_CASE, case_id="P02", action="tools_call", arguments={"v": 1})
    with pytest.raises(ConfigError, match="tool"):
        validate_config(data, "case")


def test_model_task_requires_task():
    data = dict(
        VALID_CASE,
        case_id="M01",
        level="L2",
        action="model_task",
        assertions=[{"type": "no_tool_call"}],
    )
    with pytest.raises(ConfigError, match="task"):
        validate_config(data, "case")


def test_l2_must_be_model_task():
    data = dict(VALID_CASE, level="L2")
    with pytest.raises(ConfigError, match="model_task"):
        validate_config(data, "case")


def test_load_config_missing_file(tmp_path):
    with pytest.raises(ConfigError, match="不存在"):
        load_config(tmp_path / "nope.json", "server")


def test_load_config_invalid_json(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(ConfigError, match="JSON 解析失败"):
        load_config(bad, "server")
