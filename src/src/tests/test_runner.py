"""运行编排（runner）与 CLI 的集成测试。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from mcp_eval.config import ConfigError, validate_config
from mcp_eval.records import read_jsonl
from mcp_eval.runner import run_evaluation

DELIVERY_ROOT = Path(__file__).resolve().parents[2]
SMOKE_CONFIG = "configs/runs/replay_smoke.json"


def test_replay_requires_recording():
    run = {
        "run_id": "r",
        "channel": "replay",
        "server_ref": "x.json",
        "case_glob": "*.json",
        "output_dir": "out",
    }
    with pytest.raises(ConfigError, match="recording"):
        validate_config(run, "run")


def test_dry_run_only_plans():
    outcome = run_evaluation(SMOKE_CONFIG, DELIVERY_ROOT, dry_run=True)
    assert outcome["executed"] == 0
    assert outcome["plan"]["l1_cases"] == 7
    assert outcome["plan"]["channel"] == "replay"


def test_replay_smoke_end_to_end():
    """离线冒烟：7 条 L1 用例经回放通道执行、判定并产出报告。"""
    outcome = run_evaluation(SMOKE_CONFIG, DELIVERY_ROOT)
    assert outcome["executed"] == 7

    records = read_jsonl(outcome["results"])
    assert len(records) == 7
    verdicts = {r["case_id"]: r["verdict"] for r in records}
    assert set(verdicts) == {"P01", "P02", "P03", "P04", "P05", "N01", "N02"}
    assert all(v == "pass" for v in verdicts.values())
    # 回放记录必须带 channel=replay 标记，不与真机混淆
    assert all(r["channel"] == "replay" for r in records)

    summary = json.loads(Path(outcome["summary"]).read_text(encoding="utf-8"))
    group = summary["groups"]["replay|L1|positive|-"]
    assert group["planned"] == 5 and group["pass"] == 5
    negative = summary["groups"]["replay|L1|negative|-"]
    assert negative["planned"] == 2 and negative["pass"] == 2

    report_text = Path(outcome["report"]).read_text(encoding="utf-8")
    assert "replay|L1" in report_text


def test_case_glob_no_match_raises():
    from mcp_eval.config import load_config
    from mcp_eval.runner import load_cases

    run = load_config(DELIVERY_ROOT / SMOKE_CONFIG, "run")
    run["case_glob"] = "tests/cases/none/*.json"
    with pytest.raises(ConfigError, match="未匹配"):
        load_cases(run, DELIVERY_ROOT)
