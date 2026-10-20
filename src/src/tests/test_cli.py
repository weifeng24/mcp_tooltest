"""CLI 不调用设备/模型的端到端验证。"""
import json
import shutil
from pathlib import Path

import pytest

from mcp_eval import __main__ as cli


@pytest.fixture
def project(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[2]
    for folder in ("configs", "recordings", "tests/cases"):
        shutil.copytree(root / folder, tmp_path / folder)
    monkeypatch.setattr(cli, "DELIVERY_ROOT", tmp_path)
    return tmp_path


def test_cli_smoke_then_rebuild_preserves_metrics(project, capsys):
    assert cli.main(["run", "configs/runs/replay_smoke.json"]) == 0
    outcome = json.loads(capsys.readouterr().out)
    before = Path(outcome["summary"]).read_bytes()
    batch = str(Path(outcome["results"]).parent.relative_to(project))
    assert cli.main(["rebuild", batch]) == 0
    assert Path(outcome["summary"]).read_bytes() == before


def test_cli_dry_run_rejects_missing_device_id(project, capsys):
    assert cli.main(["run", "configs/runs/l1_device.json", "--dry-run"]) == 2
    assert "device_serial" in capsys.readouterr().err


def test_cli_show_call_has_explicit_argument(project, capsys):
    assert cli.main(["show-call", "tests/cases/l1/P02_set_temp_valid.json"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["argv"][3] == "--toolscall"
    assert json.loads(output["argv"][-1])["temperature"] == 22
    assert output["device_verified"] is False


def test_catalog_dry_run_does_not_need_device_or_run_commands(project, capsys, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("dry-run不应执行adb")
    monkeypatch.setattr("mcp_eval.catalog.AdbRunner", forbidden)
    assert cli.main(["capture-catalog", "configs/servers/ark_mcp_service.json", "--service",
                     "MCPVehicleService", "--dry-run"]) == 0
    value = json.loads(capsys.readouterr().out)
    assert value["executed"] == 0
    assert len(value["files"]) == 2
    assert all("cat " in item["argv"][1] for item in value["files"])
    assert value["device_configured"] is False
