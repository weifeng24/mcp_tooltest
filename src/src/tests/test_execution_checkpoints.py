"""C02/C05：中途失败保留真实已观察片段，最后一次调用返回后检查时限。"""
import json
from pathlib import Path

import pytest

from mcp_eval.judge import judge_record
from mcp_eval.model_loop import ModelLoop
from mcp_eval.providers.base import ProviderResponse, ToolCallDecision
from mcp_eval.records import EvalRecord, read_jsonl
from mcp_eval.report import write_report
from mcp_eval.runner import _execute_item, run_evaluation

CASE = {"case_id": "P02", "level": "L1", "category": "positive", "action": "tools_call", "service": "auto",
        "tool": "s.set", "arguments": {"temperature": 22}, "expected_source": "synthetic test contract",
        "assertions": [{"type": "field_equals", "path": "success", "value": True}],
        "postconditions": [{"tool": "s.get", "arguments": {}, "path": "temperature", "value": 22}]}


def observed(case, run_id):
    return EvalRecord(run_id=run_id, case_id=case["case_id"], channel="device", action="tools_call", service="auto",
                      tool=case["tool"], arguments=case.get("arguments", {}), source_type="synthetic",
                      execution_status="completed", trace_complete=True,
                      request_raw={"method": "tools/call", "params": {"name": case["tool"], "arguments": case.get("arguments", {})}},
                      response_raw={"result": {"success": True, "temperature": 22}})


def prepare(root, cases, *, model=False):
    values = {"server.json": {"server_id": "test", "baseline_tree": "/unused", "baseline_commit": "abcdef0",
                              "device_serial": "synthetic", "services": ["auto"]},
              "run.json": {"run_id": "test", "channel": "device", "server_ref": "server.json",
                           "case_glob": "cases/*.json", "output_dir": "results"}}
    if model:
        values["model.json"] = {"model_config_id": "fake", "provider": "deepseek", "model": "fake", "api_key_env": "NOT_USED"}
        values["tools.json"] = [{"name": "s.set", "inputSchema": {"type": "object"}}]
        values["run.json"].update(model_refs=["model.json"], tools_file="tools.json")
    for case in cases:
        values[f"cases/{case['case_id']}.json"] = case
    for name, value in values.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))


@pytest.mark.parametrize("exception_type", [KeyboardInterrupt, OSError])
def test_readback_failure_preserves_completed_primary_and_report(tmp_path, monkeypatch, exception_type):
    prepare(tmp_path, [CASE, {**CASE, "case_id": "P03"}])

    class Channel:
        name = "device"
        source_type = "synthetic"

        def execute_case(self, case, run_id, timeout):
            if case["tool"] == "s.get":
                raise exception_type("readback failed")
            return observed(case, run_id)

    monkeypatch.setattr("mcp_eval.runner.build_channel", lambda *args: Channel())
    outcome = run_evaluation("run.json", tmp_path)
    rows = read_jsonl(outcome["results"])
    first = rows[0]
    assert first["response_raw"]["result"]["success"] is True
    assert first["tool"] == "s.set"
    assert first["execution_status"] == "error" and first["trace_complete"] is False
    assert first["verdict"] == "unassessed" and first["evidence"]
    if exception_type is KeyboardInterrupt:
        assert outcome["interrupted"] and outcome["executed"] == 1
        assert rows[1]["execution_status"] == "not_run"
    else:
        assert not outcome["interrupted"] and outcome["executed"] == 2
    batch = Path(outcome["manifest"]).parent
    before = Path(outcome["summary"]).read_bytes()
    write_report(outcome["results"], {"P02": CASE, "P03": {**CASE, "case_id": "P03"}}, batch, outcome["run_id"])
    assert Path(outcome["summary"]).read_bytes() == before


def test_primary_evidence_is_on_disk_before_readback(tmp_path, monkeypatch):
    prepare(tmp_path, [CASE])

    class Channel:
        name = "device"
        source_type = "synthetic"

        def execute_case(self, case, run_id, timeout):
            if case["tool"] == "s.get":
                snapshots = list((tmp_path / "results").glob("*/artifacts/item-00001.json"))
                assert snapshots, "回读之前应已保存主调用证据"
                saved = json.loads(snapshots[0].read_text())
                assert saved["response_raw"]["result"]["success"] is True
            return observed(case, run_id)

    monkeypatch.setattr("mcp_eval.runner.build_channel", lambda *args: Channel())
    assert run_evaluation("run.json", tmp_path)["counts"]["pass"] == 1


def test_interrupt_during_result_append_recovers_from_artifact(tmp_path, monkeypatch):
    prepare(tmp_path, [{**CASE, "postconditions": []}])

    class Channel:
        name = "device"
        source_type = "synthetic"

        def execute_case(self, case, run_id, timeout):
            return observed(case, run_id)

    def broken_append(path, record):
        Path(path).write_text('{"incomplete":')
        raise KeyboardInterrupt

    monkeypatch.setattr("mcp_eval.runner.build_channel", lambda *args: Channel())
    monkeypatch.setattr("mcp_eval.runner.append_jsonl", broken_append)
    outcome = run_evaluation("run.json", tmp_path)
    assert outcome["interrupted"] and outcome["counts"]["pass"] == 1
    assert len(read_jsonl(outcome["results"])) == 1


@pytest.mark.parametrize("no_call_control", [False, True])
def test_model_interruption_preserves_executed_tool_and_known_violation(tmp_path, monkeypatch, no_call_control):
    case = {"case_id": "M01", "level": "L2", "category": "negative" if no_call_control else "positive",
            "action": "model_task", "service": "auto", "task": "设置温度", "expected_source": "synthetic contract",
            "assertions": [{"type": "no_tool_call"}] if no_call_control else [
                {"type": "tool_call_matches", "name": "s.set", "arguments": {"temperature": 22}}]}
    prepare(tmp_path, [case], model=True)

    class Provider:
        rounds = 0

        def chat(self, *args, **kwargs):
            self.rounds += 1
            if self.rounds == 2:
                raise KeyboardInterrupt
            return ProviderResponse(tool_calls=[ToolCallDecision("c1", "s_set", {"temperature": 22})])

    class Channel:
        name = "device"
        source_type = "synthetic"

        def execute_case(self, case, run_id, timeout):
            return observed(case, run_id)

    monkeypatch.setattr("mcp_eval.runner.create_provider", lambda *args: Provider())
    monkeypatch.setattr("mcp_eval.runner.build_channel", lambda *args: Channel())
    outcome = run_evaluation("run.json", tmp_path)
    row = read_jsonl(outcome["results"])[0]
    assert row["response_raw"]["tool_calls"][0]["record"]["response_raw"]["result"]["success"] is True
    assert row["execution_status"] == "error" and row["trace_complete"] is False
    assert row["verdict"] == ("fail" if no_call_control else "unassessed")
    assert outcome["interrupted"] and outcome["executed"] == 1


@pytest.mark.parametrize("late_at", ["s.set", "s.get"])
def test_l1_checks_deadline_after_last_return(monkeypatch, late_at):
    clock = [0.0]
    calls = []
    case = {**CASE, "timeout_seconds": 1}
    if late_at == "s.set":
        case["postconditions"] = []

    class Channel:
        name = "device"

        def execute_case(self, current, run_id, timeout):
            calls.append(current["tool"])
            if current["tool"] == late_at:
                clock[0] = 2.0
            return observed(current, run_id)

    monkeypatch.setattr("mcp_eval.runner.time.monotonic", lambda: clock[0])
    row = _execute_item({}, case, {"run_id": "r"}, Channel(), [], {})
    assert row.execution_status == "timeout"
    assert row.latency_ms == 2000 and row.response_raw is not None
    assert judge_record(case, row).verdict != "pass"


def test_l1_checkpoint_time_is_charged_before_dispatch(monkeypatch):
    clock = [0.0]

    class Channel:
        name = "device"

        def execute_case(self, *args):
            raise AssertionError("预算耗尽后不得下发")

    def checkpoint(record):
        clock[0] = 2.0

    monkeypatch.setattr("mcp_eval.runner.time.monotonic", lambda: clock[0])
    result = _execute_item({}, {**CASE, "timeout_seconds": 1}, {"run_id": "r"}, Channel(), [], {}, checkpoint=checkpoint)
    assert result.execution_status == "timeout" and not result.trace_complete


@pytest.mark.parametrize("expire_before", ["model_request", "tool_execution"])
def test_model_checkpoint_time_is_charged_before_dispatch(expire_before):
    clock = [0.0]

    def checkpoint(record):
        if expire_before == "model_request" and record.events:
            clock[0] = 2.0
        if expire_before == "tool_execution" and record.response_raw["tool_calls"]:
            clock[0] = 2.0

    class Provider:
        def chat(self, *args, **kwargs):
            assert expire_before != "model_request", "检查点耗尽预算后不得请求模型"
            return ProviderResponse(tool_calls=[ToolCallDecision("a", "s_set", {})])

    class Executor:
        channel = "device"
        source_type = "synthetic"

        def __call__(self, *args, **kwargs):
            raise AssertionError("检查点耗尽预算后不得下发工具")

    case = {"case_id": "M01", "service": "auto", "task": "设置"}
    row = ModelLoop(Provider(), Executor(), [{"name": "s.set", "inputSchema": {"type": "object"}}],
                    clock=lambda: clock[0]).run_case(case, "r", "mock", 1, checkpoint=checkpoint)
    assert row.execution_status == "timeout"
