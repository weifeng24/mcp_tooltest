"""车端注册目录快照：仅模拟adb文件读取，不执行工具。"""
import copy
import json
import shlex

import pytest

from mcp_eval.config import ConfigError
from mcp_eval.device import AdbResult


def test_snapshot_normalizes_explicit_service_alias_without_mutating_raw():
    from mcp_eval.catalog import normalize_tools_snapshot
    raw = {"jsonrpc": "2.0", "id": 1, "result": {"tools": [
        {"name": "getTemp", "inputSchema": {"type": "object"}},
        {"name": "16777217.setTemp", "inputSchema": {"type": "object"}}]}}
    before = copy.deepcopy(raw)
    tools, bindings = normalize_tools_snapshot("MCPVehicleService", raw)
    assert tools[0]["name"] == "MCPVehicleService.getTemp"
    assert tools[1]["name"] == "16777217.setTemp"
    assert bindings[0]["original_name"] == "getTemp"
    assert bindings[0]["alias_verified_on_device"] is False
    assert raw == before


def test_snapshot_without_complete_schema_rejected():
    from mcp_eval.catalog import normalize_tools_snapshot
    with pytest.raises(ConfigError):
        normalize_tools_snapshot("Vehicle", {"tools": [{"name": "getTemp"}]})


def test_capture_uses_only_read_only_file_commands(tmp_path):
    from mcp_eval.catalog import capture_catalog
    server = {"server_id": "test", "device_serial": "test-device", "services": ["MCPVehicleService"],
              "dump_dir": "/data/mcp/dump"}
    calls = []
    def runner(args, timeout):
        calls.append(args)
        command = shlex.split(args[1])
        assert command[0] == "cat"
        if "tools_" in command[1]:
            data = {"tools": [{"name": "getTemp", "inputSchema": {"type": "object"}}]}
        else:
            data = {"resources": [{"uri": "dds://status"}]}
        return AdbResult(0, json.dumps(data), "", 1)
    outcome = capture_catalog(server, tmp_path, runner=runner)
    catalog = json.loads((tmp_path / outcome["catalog"]).read_text())
    assert len(calls) == 2
    assert catalog["catalog_status"] == "complete"
    assert catalog["source"]["kind"] == "registration_dump"
    assert catalog["source"]["runtime_tools_list_tested"] is False
    assert catalog["source"]["resource_values_read"] is False
    assert catalog["tools"][0]["name"] == "MCPVehicleService.getTemp"


def test_missing_dump_keeps_partial_evidence(tmp_path):
    from mcp_eval.catalog import capture_catalog
    server = {"server_id": "test", "device_serial": "test-device", "services": ["Vehicle"], "dump_dir": "/data/mcp/dump"}
    outcome = capture_catalog(server, tmp_path, runner=lambda *args: AdbResult(1, "", "No such file", 1))
    assert outcome["catalog_status"] == "failed"
    manifest = json.loads((tmp_path / outcome["manifest"]).read_text())
    assert len(manifest["files"]) == 2
    assert all(item["status"] == "error" for item in manifest["files"])


def test_partial_tool_catalog_not_loaded_for_model(tmp_path):
    from mcp_eval.runner import load_tools
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps({"tools_status": "partial", "tools": [
        {"name": "Service.getTemp", "inputSchema": {"type": "object"}}]}))
    with pytest.raises(ConfigError, match="不完整"):
        load_tools({"tools_file": "catalog.json"}, tmp_path)


def test_snapshot_service_name_cannot_escape_dump_directory():
    from mcp_eval.catalog import catalog_plan
    with pytest.raises(ConfigError):
        catalog_plan({"services": ["../../etc"], "dump_dir": "/data/mcp/dump"})


@pytest.mark.parametrize("timeout", [float("nan"), float("inf")])
def test_capture_rejects_nonfinite_budget_before_io(tmp_path, timeout):
    from mcp_eval.catalog import capture_catalog
    server = {"server_id": "test", "device_serial": "test-device", "services": ["Vehicle"], "dump_dir": "/data/mcp/dump"}
    def forbidden(*args):
        raise AssertionError("非法预算不得开始采集")
    with pytest.raises(ConfigError):
        capture_catalog(server, tmp_path, runner=forbidden, timeout=timeout)
