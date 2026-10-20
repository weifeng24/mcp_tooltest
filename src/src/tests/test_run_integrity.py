"""批次隔离、固定计划与输入预检。"""
import json
from pathlib import Path

import pytest

from mcp_eval.config import ConfigError
from mcp_eval.records import EvalRecord, read_jsonl
from mcp_eval.report import summarize, render_markdown
from mcp_eval.runner import load_tools, run_evaluation


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def prepare(root):
    save(root / "server.json", {"server_id": "test", "baseline_tree": "/not-used",
         "baseline_commit": "abcdef0", "device_serial": "test-only", "services": ["service"]})
    for case_id in ("P01", "P02"):
        save(root / f"cases/{case_id}.json", {"case_id": case_id, "action": "tools_call", "level": "L1",
             "category": "positive", "service": "service", "tool": "service.tool", "arguments": {},
             "assertions": [{"type": "field_equals", "path": "success", "value": True}], "expected_source": "fixture"})
    run = {"run_id": "fixed-label", "channel": "device", "server_ref": "server.json",
           "case_glob": "cases/*.json", "output_dir": "results"}
    save(root / "run.json", run)
    return run


class InterruptingChannel:
    name = "device"
    source_type = "synthetic"

    def execute_case(self, case, run_id, timeout=30):
        if case["case_id"] == "P02":
            raise OSError("synthetic device failure")
        return EvalRecord(run_id=run_id, case_id=case["case_id"], channel="device", action="tools_call",
                          service="service", execution_status="completed", trace_complete=True,
                          source_type="synthetic", response_raw={"result": {"success": True}})


def test_partial_failure_preserves_all_plan_items_and_old_batches(tmp_path, monkeypatch):
    prepare(tmp_path)
    monkeypatch.setattr("mcp_eval.runner.build_channel", lambda *args: InterruptingChannel())
    first = run_evaluation("run.json", tmp_path)
    old = Path(first["results"]).read_bytes()
    second = run_evaluation("run.json", tmp_path)
    assert first["results"] != second["results"]
    assert Path(first["results"]).read_bytes() == old
    records = read_jsonl(first["results"])
    assert len(records) == 2
    assert [r["verdict"] for r in records] == ["pass", "unassessed"]
    summary = json.loads(Path(first["summary"]).read_text())
    assert summary["total"] == 2
    assert next(iter(summary["groups"].values()))["judge_coverage"] == 0.5
    assert Path(first["manifest"]).exists()


def test_fixed_plan_includes_missing_record():
    case = {"P01": {"level": "L1", "category": "positive"}, "P02": {"level": "L1", "category": "positive"}}
    planned = [{"item_id": name, "case_id": name, "channel": "replay", "model": None,
                "level": "L1", "category": "positive", "repeat_index": 0} for name in case]
    rec = EvalRecord(run_id="r", case_id="P01", channel="replay", action="tools_call", service="s",
                     item_id="P01", verdict="pass", trace_complete=True, execution_status="completed")
    summary = summarize([rec], case, planned)
    group = next(iter(summary["groups"].values()))
    assert (group["planned"], group["pass"], group["unassessed"]) == (2, 1, 1)
    assert group["judge_coverage"] == 0.5


def test_dry_run_checks_model_refs(tmp_path):
    run = prepare(tmp_path)
    run["model_refs"] = ["missing.json"]
    save(tmp_path / "run.json", run)
    with pytest.raises(ConfigError):
        run_evaluation("run.json", tmp_path, dry_run=True)


def test_tools_loader_accepts_complete_jsonrpc_response(tmp_path):
    tools = [{"name": "service.tool", "inputSchema": {"type": "object"}}]
    save(tmp_path / "tools.json", {"jsonrpc": "2.0", "id": 1, "result": {"tools": tools}})
    assert load_tools({"tools_file": "tools.json"}, tmp_path) == tools


def test_duplicate_case_ids_rejected_before_execution(tmp_path):
    prepare(tmp_path)
    save(tmp_path / "cases/duplicate.json", json.loads((tmp_path / "cases/P01.json").read_text()))
    with pytest.raises(ConfigError, match="重复"):
        run_evaluation("run.json", tmp_path, dry_run=True)


def test_markdown_group_separator_escaped():
    summary = {"total": 1, "groups": {"replay|L1|positive|-": {
        "planned": 1, "pass": 1, "fail": 0, "unassessed": 0,
        "pass_rate_planned": 1, "judge_coverage": 1}}, "failure_categories": {}}
    text = render_markdown(summary, [], "r")
    assert "replay\\|L1\\|positive\\|-" in text


def test_keyboard_interrupt_still_writes_missing_items_and_report(tmp_path, monkeypatch):
    prepare(tmp_path)

    class Stopped(InterruptingChannel):
        def execute_case(self, *args, **kwargs):
            raise KeyboardInterrupt

    monkeypatch.setattr("mcp_eval.runner.build_channel", lambda *args: Stopped())
    outcome = run_evaluation("run.json", tmp_path)
    assert outcome["interrupted"] is True
    assert outcome["executed"] == 1
    assert outcome["counts"] == {"pass": 0, "fail": 0, "unassessed": 2}
    # 第一条已经进入执行器，中断不证明远端未执行；后续条目才是not_run。
    assert [row["execution_status"] for row in read_jsonl(outcome["results"])] == ["error", "not_run"]


def test_output_path_cannot_escape_delivery(tmp_path):
    run = prepare(tmp_path)
    run["output_dir"] = "../outside"
    save(tmp_path / "run.json", run)
    with pytest.raises(ConfigError, match="超出"):
        run_evaluation("run.json", tmp_path, dry_run=True)


def test_second_repetition_without_recording_stays_in_denominator(tmp_path):
    root = Path(__file__).resolve().parents[2]
    import shutil
    for folder in ("configs", "recordings", "tests/cases"):
        shutil.copytree(root / folder, tmp_path / folder)
    path = tmp_path / "configs/runs/replay_smoke.json"
    run = json.loads(path.read_text())
    run["repeat"] = 2
    save(path, run)
    outcome = run_evaluation("configs/runs/replay_smoke.json", tmp_path)
    assert outcome["counts"] == {"pass": 8, "fail": 0, "unassessed": 8}
    assert len(read_jsonl(outcome["results"])) == 16


def test_different_cases_with_same_request_get_independent_identities(tmp_path):
    prepare(tmp_path)
    # 固定计划里的不同用例不因请求相同而折叠；device 替身每条真实执行一次。
    from unittest.mock import patch
    class Good(InterruptingChannel):
        def execute_case(self, case, run_id, timeout=30):
            return super().execute_case({**case, "case_id": "P01"}, run_id, timeout)
    # 故意错误身份的执行器应被拒绝，不能静默改写结果归属。
    with patch("mcp_eval.runner.build_channel", return_value=Good()):
        outcome = run_evaluation("run.json", tmp_path)
        assert outcome["counts"] == {"pass": 1, "fail": 0, "unassessed": 1}
        assert "身份" in read_jsonl(outcome["results"])[1]["verdict_reason"]
