"""报告器的单元测试。"""
from __future__ import annotations

import json

from mcp_eval.records import EvalRecord, append_jsonl
from mcp_eval.report import summarize, write_report

CASES = {
    "P01": {"level": "L1", "category": "positive"},
    "P02": {"level": "L1", "category": "positive"},
    "N01": {"level": "L1", "category": "negative"},
    "M01": {"level": "L2", "category": "positive"},
}


def make_record(case_id: str, verdict: str, channel: str = "device",
                latency: int | None = 100, model: str | None = None) -> EvalRecord:
    return EvalRecord(
        run_id="r1",
        case_id=case_id,
        channel=channel,
        action="tools_call",
        service="s",
        model=model,
        execution_status="completed" if verdict in ("pass", "fail") else "blocked",
        verdict=verdict,
        latency_ms=latency,
    )


def test_summarize_counts_and_rates():
    records = [
        make_record("P01", "pass"),
        make_record("P02", "fail"),
        make_record("N01", "unassessed", latency=None),
    ]
    summary = summarize(records, CASES)
    l1_pos = summary["groups"]["device|L1|positive|-"]
    assert l1_pos["planned"] == 2
    assert l1_pos["pass"] == 1 and l1_pos["fail"] == 1
    assert l1_pos["pass_rate_planned"] == 0.5
    assert l1_pos["judge_coverage"] == 1.0
    assert l1_pos["pass_rate_judged"] == 0.5
    l1_neg = summary["groups"]["device|L1|negative|-"]
    assert l1_neg["unassessed"] == 1
    assert l1_neg["pass_rate_judged"] is None  # 分母 0 → 不适用


def test_summarize_separates_channel_and_model():
    records = [
        make_record("P01", "pass", channel="device"),
        make_record("P01", "pass", channel="replay"),
        make_record("M01", "pass", model="deepseek-chat"),
        make_record("M01", "fail", model="kimi-coding"),
    ]
    summary = summarize(records, CASES)
    assert "device|L1|positive|-" in summary["groups"]
    assert "replay|L1|positive|-" in summary["groups"]
    assert "device|L2|positive|deepseek-chat" in summary["groups"]
    assert "device|L2|positive|kimi-coding" in summary["groups"]


def test_failure_categories_counted():
    records = [
        make_record("P01", "fail"),
        make_record("P02", "fail"),
    ]
    records[0].error_category = None
    records[1].error_category = "timeout"
    summary = summarize(records, CASES)
    assert summary["failure_categories"] == {"assertion_failed": 1, "timeout": 1}


def test_latency_stats():
    records = [
        make_record("P01", "pass", latency=100),
        make_record("P02", "pass", latency=300),
    ]
    g = summarize(records, CASES)["groups"]["device|L1|positive|-"]["latency_ms"]
    assert g["median"] == 200 and g["min"] == 100 and g["max"] == 300 and g["samples"] == 2


def test_write_report_rebuild_is_deterministic(tmp_path):
    """从保存的结果重建报告：两次生成的指标必须一致（报告可复现）。"""
    results = tmp_path / "results.jsonl"
    append_jsonl(results, make_record("P01", "pass"))
    append_jsonl(results, make_record("P02", "fail"))
    append_jsonl(results, make_record("N01", "unassessed", latency=None))

    out1 = tmp_path / "out1"
    out2 = tmp_path / "out2"
    s1, r1 = write_report(results, CASES, out1, "run-x")
    s2, r2 = write_report(results, CASES, out2, "run-x")

    m1 = json.loads(s1.read_text(encoding="utf-8"))
    m2 = json.loads(s2.read_text(encoding="utf-8"))
    assert m1["groups"] == m2["groups"]
    assert m1["failure_categories"] == m2["failure_categories"]

    text = r1.read_text(encoding="utf-8")
    assert "device|L1|positive|-" in text
    assert "P02" in text and "N01" in text  # 失败与无法判断都在明细里
    assert "回放数据仅供开发自测" in text
