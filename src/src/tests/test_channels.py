"""device / replay 双通道的单元测试（离线，无真实设备）。"""
from __future__ import annotations

from pathlib import Path

import pytest

from mcp_eval.config import load_config
from mcp_eval.device import AdbResult, DeviceChannel, build_test_config, extract_jsonrpc
from mcp_eval.records import EvalRecord, append_jsonl
from mcp_eval.replay import ReplayChannel

CASE = {
    "case_id": "P02",
    "level": "L1",
    "category": "positive",
    "service": "auto",
    "action": "tools_call",
    "tool": "HvacService.setTemp",
    "arguments": {"temperature": 22},
}

OK_STDOUT = (
    "10-13 15:00:00.123 I/mcp_service: starting client test\n"
    '10-13 15:00:00.456 I/mcp_service: {"jsonrpc": "2.0", "result": '
    '{"content": [{"type": "text", "text": "ok"}], "success": true}, "id": 1}\n'
    "10-13 15:00:00.789 I/mcp_service: done\n"
)


class FakeRunner:
    """按预设结果依次返回的 runner，用于离线测试。"""

    def __init__(self, results: list[AdbResult]) -> None:
        self.results = list(results)
        self.calls: list[list[str]] = []

    def __call__(self, args: list[str], timeout: int) -> AdbResult:
        self.calls.append(args)
        assert self.results, "FakeRunner 结果用尽"
        return self.results.pop(0)


def ok(result_stdout: str = OK_STDOUT) -> AdbResult:
    return AdbResult(returncode=0, stdout=result_stdout, stderr="", latency_ms=120)


# ---------- extract_jsonrpc ----------


def test_extract_jsonrpc_from_noisy_stdout():
    found = extract_jsonrpc(OK_STDOUT)
    assert len(found) == 1
    assert found[0]["result"]["success"] is True


def test_extract_jsonrpc_ignores_plain_logs():
    assert extract_jsonrpc("hello\n[1] not json at all\n") == []


def test_extract_jsonrpc_multiple_objects():
    text = '{"jsonrpc":"2.0","result":{"tools":[]},"id":1}\n{"jsonrpc":"2.0","error":{"code":-32602,"message":"Unknown tool"},"id":2}'
    assert len(extract_jsonrpc(text)) == 2


# ---------- build_test_config ----------


def test_build_test_config_tools_call():
    cfg = build_test_config(CASE)
    call = cfg["client_tests"]["mcp_interface"]["test_tools_call"]
    assert call["name"] == "HvacService.setTemp"
    assert call["arguments"] == {"temperature": 22}


def test_build_test_config_tools_list():
    case = {**CASE, "action": "tools_list"}
    interface = build_test_config(case)["client_tests"]["mcp_interface"]
    assert interface["test_tools_list"] is True
    assert "test_tools_call" not in interface


def test_build_test_config_rejects_unknown_action():
    with pytest.raises(ValueError, match="model_task"):
        build_test_config({**CASE, "action": "model_task"})


# ---------- DeviceChannel ----------


def device_with(results: list[AdbResult]) -> DeviceChannel:
    return DeviceChannel(runner=FakeRunner(results))


def test_device_success_path_completed():
    ch = device_with([ok()])
    record = ch.execute_case(CASE, "run1")
    assert record.execution_status == "completed"
    assert record.response_raw["result"]["success"] is True
    assert record.latency_ms == 120
    assert record.channel == "device"


def test_device_timeout_mapped():
    ch = device_with([
        AdbResult(returncode=-1, stdout="", stderr="timeout", latency_ms=30000, timed_out=True),
    ])
    record = ch.execute_case(CASE, "run1")
    assert record.execution_status == "timeout"
    assert record.error_category == "adb_timeout_remote_state_unknown"
    assert not record.trace_complete


def test_device_exit_nonzero():
    ch = device_with([
        AdbResult(returncode=1, stdout=OK_STDOUT, stderr="err", latency_ms=50),
    ])
    record = ch.execute_case(CASE, "run1")
    assert record.execution_status == "error"
    assert record.error_category == "exit_nonzero"
    # 退出码非零但仍保留已解析的响应，便于诊断
    assert record.response_raw is not None


def test_device_parse_failed_when_no_json():
    ch = device_with([ok("plain log only")])
    record = ch.execute_case(CASE, "run1")
    assert record.execution_status == "error"
    assert record.error_category == "response_missing"


def test_device_command_failure_preserves_diagnostics():
    ch = device_with([AdbResult(returncode=1, stdout="", stderr="denied", latency_ms=10)])
    record = ch.execute_case(CASE, "run1")
    assert record.execution_status == "error"
    assert record.error_category == "exit_nonzero"
    assert record.stderr == "denied"


# ---------- ReplayChannel ----------


def write_recording(path, **overrides) -> None:
    record = EvalRecord(
        run_id="device-run-0",
        case_id=CASE["case_id"],
        channel="device",
        action=CASE["action"],
        service=CASE["service"],
        tool=CASE["tool"],
        arguments=CASE["arguments"],
        response_raw={"result": {"success": True}},
        execution_status="completed",
        latency_ms=88,
        **overrides,
    )
    append_jsonl(path, record)


def test_replay_hit_returns_recorded(tmp_path):
    rec = tmp_path / "rec.jsonl"
    write_recording(rec)
    channel = ReplayChannel(rec)
    record = channel.execute_case(CASE, "run-replay")
    assert record.channel == "replay"
    assert record.run_id == "run-replay"
    assert record.response_raw["result"]["success"] is True
    assert record.latency_ms == 88
    assert str(rec) in record.evidence


def test_replay_miss_blocked_not_faked(tmp_path):
    rec = tmp_path / "rec.jsonl"
    write_recording(rec)
    channel = ReplayChannel(rec)
    other = {**CASE, "arguments": {"temperature": 30}}
    record = channel.execute_case(other, "run-replay")
    assert record.execution_status == "blocked"
    assert record.error_category == "no_recording"
    assert record.response_raw is None


def test_replay_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        ReplayChannel(tmp_path / "none.jsonl")


def test_replay_matches_real_case_file(tmp_path):
    """用真实用例文件走一遍：录制与回放使用同一 case JSON，签名必须匹配。"""
    case_file = (
        Path(__file__).resolve().parents[2]
        / "tests" / "cases" / "l1" / "P02_set_temp_valid.json"
    )
    case = load_config(case_file, "case")
    rec = tmp_path / "rec.jsonl"
    write_recording(rec)
    record = ReplayChannel(rec).execute_case(case, "r")
    assert record.execution_status == "completed"
