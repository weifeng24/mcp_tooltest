"""报告以执行前固定的 manifest 为分母，缺失结果保留为无法判断。"""
from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any

from .records import EvalRecord, read_jsonl


def complete_records(records: list[EvalRecord], planned_items: list[dict]) -> list[EvalRecord]:
    planned = {item["item_id"]: item for item in planned_items}
    if len(planned) != len(planned_items):
        raise ValueError("manifest 中 item_id 重复")
    indexed = {}
    for record in records:
        if record.item_id not in planned or record.item_id in indexed:
            raise ValueError(f"结果条目不在计划中或重复: {record.item_id}")
        item = planned[record.item_id]
        if (record.case_id, record.model, record.channel, record.repeat_index) != (
                item["case_id"], item.get("model"), item["channel"], item.get("repeat_index", 0)):
            raise ValueError(f"结果身份与计划不符: {record.item_id}")
        indexed[record.item_id] = record
    return [indexed.get(item["item_id"]) or EvalRecord(
        run_id="", case_id=item["case_id"], item_id=item["item_id"], model=item.get("model"),
        repeat_index=item.get("repeat_index", 0), channel=item["channel"], action=item.get("action", "unknown"),
        service="", execution_status="not_run", error_category="missing_record", verdict="unassessed",
        verdict_reason="计划条目未取得执行结果") for item in planned_items]


def _latency(values):
    return {"median": statistics.median(values) if values else None,
            "min": min(values) if values else None, "max": max(values) if values else None, "samples": len(values)}


def summarize(records: list[EvalRecord], cases: dict[str, dict], planned_items: list[dict]) -> dict[str, Any]:
    normalized = complete_records(records, planned_items)
    groups, failures = {}, {}
    for item, record in zip(planned_items, normalized):
        case = cases.get(item["case_id"])
        if case is None:
            raise ValueError(f"缺少冻结用例定义: {item['case_id']}")
        key = "|".join([item["channel"], case["level"], case["category"], item.get("model") or "-"])
        group = groups.setdefault(key, {"planned": 0, "pass": 0, "fail": 0, "unassessed": 0,
                                        "sources": set(), "latencies": {v: [] for v in ("pass", "fail", "unassessed")}})
        verdict = record.verdict or "unassessed"
        if verdict not in ("pass", "fail", "unassessed"):
            raise ValueError(f"非法判定: {verdict}")
        group["planned"] += 1
        group[verdict] += 1
        group["sources"].add(record.source_type)
        if record.execution_status == "completed" and record.latency_ms is not None:
            group["latencies"][verdict].append(record.latency_ms)
        if verdict == "fail":
            category = record.error_category or "assertion_failed"
            failures[category] = failures.get(category, 0) + 1
    for group in groups.values():
        n, p, f = group["planned"], group["pass"], group["fail"]
        group.update(pass_rate_planned=p / n if n else None, judge_coverage=(p + f) / n if n else None,
                     pass_rate_judged=p / (p + f) if p + f else None,
                     source_types=sorted(group.pop("sources")))
        latencies = group.pop("latencies")
        group["latency_by_verdict"] = {v: _latency(values) for v, values in latencies.items()}
        group["latency_ms"] = _latency(latencies["pass"])
    return {"schema_version": 2, "total": len(planned_items), "observed": len(records),
            "groups": dict(sorted(groups.items())), "failure_categories": dict(sorted(failures.items()))}


def _cell(value):
    return str(value).replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def _pct(value):
    return "不适用" if value is None else f"{value * 100:.1f}%"


def render_markdown(summary: dict, records: list[EvalRecord], run_id: str) -> str:
    lines = [f"# 评测报告（run: {_cell(run_id)}）", "", f"- 计划总数：{summary['total']}",
             "- 回放数据仅供开发自测；device 标签也须结合 source_type、原始证据和版本快照解释。",
             "- 合成数据不能支撑真机结论；时延按判定分组，未知值不填零。", "", "## 指标汇总", "",
             "| 分组 | 计划 | 通过 | 失败 | 无法判断 | 计划内通过率 | 判定覆盖率 |",
             "|---|---|---|---|---|---|---|"]
    source_lines = []
    for key, group in summary["groups"].items():
        lines.append(f"| {_cell(key)} | {group['planned']} | {group['pass']} | {group['fail']} | "
                     f"{group['unassessed']} | {_pct(group['pass_rate_planned'])} | {_pct(group['judge_coverage'])} |")
        if group.get("source_types"):
            source_lines.append(f"来源 `{_cell(key)}`：{', '.join(group['source_types'])}。")
    lines += ["", *source_lines, "", "## 逐项判定与证据", "",
              "| item | case | 模型 | 重复序号 | 状态 | 判定 | 原因 | 证据 |",
              "|---|---|---|---|---|---|---|---|"]
    for record in records:
        links = ", ".join(record.evidence) or "未提供"
        values = [record.item_id, record.case_id, record.model or "-", record.repeat_index,
                  record.execution_status, record.verdict or "unassessed", record.verdict_reason or "", links]
        lines.append("| " + " | ".join(_cell(v) for v in values) + " |")
    lines += ["", "## 失败类别", ""]
    lines += [f"- {_cell(k)}: {v}" for k, v in summary["failure_categories"].items()] or ["- 无已判定失败"]
    return "\n".join(lines) + "\n"


def write_report(results_path: str | Path, cases: dict[str, dict], out_dir: str | Path,
                 run_id: str, planned_items: list[dict] | None = None) -> tuple[Path, Path]:
    path, out = Path(results_path), Path(out_dir)
    if planned_items is None:
        manifest = json.loads((path.parent / "manifest.json").read_text(encoding="utf-8"))
        planned_items = manifest["planned_items"]
    records = [EvalRecord.from_dict(value) for value in read_jsonl(path)] if path.exists() else []
    summary = summarize(records, cases, planned_items)
    out.mkdir(parents=True, exist_ok=True)
    summary_path, report_path = out / "summary.json", out / "report.md"
    summary_path.write_text(json.dumps({"run_id": run_id, **summary}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_path.write_text(render_markdown(summary, complete_records(records, planned_items), run_id), encoding="utf-8")
    return summary_path, report_path
