"""报告器：从结果 JSONL 重建分层指标与 Markdown 报告。

指标口径（与 docs/design.md §6 一致）：
- 分母固定为计划条目数 N；P + F + U = N
- 计划内通过率 = P / N；判定覆盖率 = (P + F) / N；已判定通过率 = P / (P + F)
- 分母为 0 时指标为 None（不适用），不填 0 或 100%
- device 与 replay 通道分组统计，结论以 device 为准
"""
from __future__ import annotations

import json
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .records import EvalRecord, read_jsonl


def summarize(records: list[EvalRecord], cases: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """按 (channel, level, category, model) 分组统计。"""
    groups: dict[str, dict[str, Any]] = {}
    for record in records:
        case = cases.get(record.case_id, {})
        key = "|".join(
            [
                record.channel,
                case.get("level", "?"),
                case.get("category", "?"),
                record.model or "-",
            ]
        )
        group = groups.setdefault(
            key, {"planned": 0, "pass": 0, "fail": 0, "unassessed": 0, "latencies": []}
        )
        group["planned"] += 1
        verdict = record.verdict or "unassessed"
        group[verdict] = group.get(verdict, 0) + 1
        if record.execution_status == "completed" and record.latency_ms is not None:
            group["latencies"].append(record.latency_ms)

    out_groups = {}
    for key, g in sorted(groups.items()):
        n, p, f, u = g["planned"], g["pass"], g["fail"], g["unassessed"]
        assert p + f + u == n, f"分组 {key} 计数不守恒: {p}+{f}+{u} != {n}"
        judged = p + f
        out_groups[key] = {
            "planned": n,
            "pass": p,
            "fail": f,
            "unassessed": u,
            "pass_rate_planned": p / n if n else None,
            "judge_coverage": judged / n if n else None,
            "pass_rate_judged": p / judged if judged else None,
            "latency_ms": {
                "median": statistics.median(g["latencies"]) if g["latencies"] else None,
                "min": min(g["latencies"]) if g["latencies"] else None,
                "max": max(g["latencies"]) if g["latencies"] else None,
                "samples": len(g["latencies"]),
            },
        }
    return {
        "total": len(records),
        "groups": out_groups,
        "failure_categories": _count_failure_categories(records),
    }


def _count_failure_categories(records: list[EvalRecord]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for r in records:
        if r.verdict == "fail":
            key = r.error_category or "assertion_failed"
            counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def render_markdown(
    summary: dict[str, Any], records: list[EvalRecord], run_id: str
) -> str:
    lines = [
        f"# 评测报告（run: {run_id}）",
        "",
        f"- 记录总数：{summary['total']}",
        "- 分组口径：通道|层次|类别|模型；回放数据仅供开发自测，结论以 device 通道为准",
        "",
        "## 指标汇总",
        "",
        "| 分组 | 计划 | 通过 | 失败 | 无法判断 | 计划内通过率 | 判定覆盖率 |",
        "|---|---|---|---|---|---|---|",
    ]
    for key, g in summary["groups"].items():
        lines.append(
            f"| {key} | {g['planned']} | {g['pass']} | {g['fail']} | {g['unassessed']} "
            f"| {_pct(g['pass_rate_planned'])} | {_pct(g['judge_coverage'])} |"
        )
    lines += ["", "## 失败与无法判断明细", "", "| case | 状态 | 判定 | 原因 |", "|---|---|---|---|"]
    problems = [r for r in records if r.verdict in ("fail", "unassessed")]
    if not problems:
        lines.append("| — | — | — | 无 |")
    for r in problems:
        reason = (r.verdict_reason or "").replace("|", "\\|")
        lines.append(f"| {r.case_id} | {r.execution_status} | {r.verdict} | {reason} |")
    if summary["failure_categories"]:
        lines += ["", "## 失败类别分布", ""]
        for category, count in summary["failure_categories"].items():
            lines.append(f"- {category}: {count}")
    lines += [
        "",
        f"生成时间：{datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds')}",
        "",
    ]
    return "\n".join(lines)


def _pct(value: float | None) -> str:
    return "不适用" if value is None else f"{value * 100:.1f}%"


def write_report(
    results_path: str | Path,
    cases: dict[str, dict[str, Any]],
    out_dir: str | Path,
    run_id: str,
) -> tuple[Path, Path]:
    """从保存的结果文件重建 summary.json 与 report.md，返回两者路径。"""
    records = [EvalRecord.from_dict(r) for r in read_jsonl(results_path)]
    summary = summarize(records, cases)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    summary_path = out / "summary.json"
    summary_path.write_text(
        json.dumps({"run_id": run_id, **summary}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    report_path = out / "report.md"
    report_path.write_text(render_markdown(summary, records, run_id), encoding="utf-8")
    return summary_path, report_path
