"""只读核对固定报告批次；仅使用标准库，不导入或执行被测产品。"""
import hashlib
import json
import statistics
import sys
from collections import Counter
from pathlib import Path


root = Path.cwd().resolve()
expected_root = Path(__file__).resolve().parent.parent / "sandbox"
if root != expected_root:
    raise SystemExit(f"工作目录不符：{root}")

batch = "fixtures/report-batch/"
inputs = {}


def read_bytes(relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"读取路径超出 sandbox：{relative}")
    data = path.read_bytes()
    inputs[relative] = data
    return data


def read_json(relative):
    return json.loads(read_bytes(relative))


def read_jsonl(relative):
    return [json.loads(line) for line in read_bytes(relative).decode("utf-8").splitlines() if line.strip()]


def latency_stats(values):
    return {
        "median": statistics.median(values) if values else None,
        "min": min(values) if values else None,
        "max": max(values) if values else None,
        "samples": len(values),
    }


manifest = read_json(batch + "manifest.json")
records = read_jsonl(batch + "results.jsonl")
summary = read_json(batch + "summary.json")
report = read_bytes(batch + "report.md").decode("utf-8")
recording = read_jsonl(batch + "recording-input.jsonl")
config = read_json("configs/runs/replay_smoke.json")
read_bytes("README.md")

plan = manifest["planned_items"]
plan_ids = [item["item_id"] for item in plan]
result_ids = [record["item_id"] for record in records]
by_id = {record["item_id"]: record for record in records}
cases = {case["case_id"]: case for case in manifest["inputs"]["cases"]}
checks = {
    "unique_plan_ids": len(set(plan_ids)) == len(plan_ids),
    "unique_result_ids": len(set(result_ids)) == len(result_ids),
    "all_planned_items_have_results": set(plan_ids) <= set(result_ids),
    "no_unplanned_results": set(result_ids) <= set(plan_ids),
    "same_run_id": all(record["run_id"] == manifest["run_id"] for record in records),
}
if not all(checks.values()):
    print(json.dumps({"checks": checks}, ensure_ascii=False, indent=2))
    raise SystemExit(1)

identity_fields = ("case_id", "channel", "model", "repeat_index", "action")
checks["result_identities_match_plan"] = all(
    all(by_id[item["item_id"]].get(key) == item.get(key) for key in identity_fields)
    for item in plan
)
checks["case_categories_match_plan"] = all(
    (item["level"], item["category"]) == (cases[item["case_id"]]["level"], cases[item["case_id"]]["category"])
    for item in plan
)

groups = {}
failures = Counter()
artifact_matches = {}
item_details = []
recording_by_case = {record["case_id"]: record for record in recording}
recording_differences = []
for item in plan:
    record = by_id[item["item_id"]]
    case = cases[item["case_id"]]
    key = "|".join((item["channel"], case["level"], case["category"], item.get("model") or "-"))
    groups.setdefault(key, []).append(record)
    if record["verdict"] == "fail":
        failures[record.get("error_category") or "assertion_failed"] += 1
    artifact_path = batch + f"artifacts/{item['item_id']}.json"
    artifact_matches[item["item_id"]] = read_json(artifact_path) == record
    item_details.append({
        "item_id": item["item_id"], "case_id": item["case_id"], "category": case["category"],
        **{key: record.get(key) for key in (
            "execution_status", "verdict", "verdict_reason", "error_category", "source_type",
            "trace_complete", "latency_ms", "model", "response_raw",
        )},
        "postcondition_readbacks": [
            {key: checked.get(key) for key in ("tool", "arguments", "response_raw", "execution_status", "source_type", "trace_complete")}
            for checked in record.get("provenance", {}).get("postconditions", [])
        ],
        "fixture_marker": record.get("provenance", {}).get("skill_eval_fixture"),
    })
    source_case_id = record.get("provenance", {}).get("source_case_id")
    source = recording_by_case.get(source_case_id)
    if source is not None:
        fields = ("action", "tool", "arguments", "response_raw", "execution_status", "trace_complete", "source_type")
        differences = {
            field: {"recording_input": source.get(field), "saved_result": record.get(field)}
            for field in fields if source.get(field) != record.get(field)
        }
        if differences:
            recording_differences.append({"item_id": item["item_id"], "case_id": item["case_id"], "differences": differences})

computed_groups = {}
for key, rows in sorted(groups.items()):
    counts = Counter(record["verdict"] for record in rows)
    p, f, n = counts["pass"], counts["fail"], len(rows)
    latencies = {
        verdict: latency_stats([
            record["latency_ms"] for record in rows
            if record["verdict"] == verdict and record["execution_status"] == "completed" and record["latency_ms"] is not None
        ]) for verdict in ("pass", "fail", "unassessed")
    }
    computed_groups[key] = {
        "planned": n, **{verdict: counts[verdict] for verdict in ("pass", "fail", "unassessed")},
        "pass_rate_planned": p / n,
        "judge_coverage": (p + f) / n,
        "pass_rate_judged": p / (p + f) if p + f else None,
        "source_types": sorted({record["source_type"] for record in rows}),
        "latency_by_verdict": latencies, "latency_ms": latencies["pass"],
    }

computed_summary = {
    "run_id": manifest["run_id"], "schema_version": 2, "total": len(plan), "observed": len(records),
    "groups": computed_groups, "failure_categories": dict(sorted(failures.items())),
}
checks["summary_all_fields_match"] = computed_summary == summary
checks["all_artifacts_equal_results"] = all(artifact_matches.values())
checks["report_run_id_and_total_match"] = (
    f"# 评测报告（run: {manifest['run_id']}）" in report
    and f"- 计划总数：{len(plan)}" in report
)

expected_group_lines = []
for key, group in computed_groups.items():
    escaped_key = key.replace("|", "\\|")
    expected_group_lines.append(
        f"| {escaped_key} | {group['planned']} | {group['pass']} | {group['fail']} | {group['unassessed']} | "
        f"{group['pass_rate_planned'] * 100:.1f}% | {group['judge_coverage'] * 100:.1f}% |"
    )
expected_item_lines = []
for item in plan:
    record = by_id[item["item_id"]]
    cells = [record["item_id"], record["case_id"], record.get("model") or "-", record["repeat_index"],
             record["execution_status"], record["verdict"], record["verdict_reason"], ", ".join(record["evidence"])]
    expected_item_lines.append("| " + " | ".join(str(value).replace("|", "\\|") for value in cells) + " |")
checks["report_group_rows_match"] = all(line in report.splitlines() for line in expected_group_lines)
checks["report_item_rows_match"] = all(line in report.splitlines() for line in expected_item_lines)
checks["report_failure_counts_match"] = all(f"- {key}: {value}" in report.splitlines() for key, value in failures.items())

frozen_config = dict(manifest["inputs"]["run"])
frozen_config["run_id"] = manifest["requested_run_id"]
checks["current_replay_config_matches_frozen_config"] = frozen_config == config
checks["recording_hash_matches_manifest"] = (
    hashlib.sha256(inputs[batch + "recording-input.jsonl"]).hexdigest() == manifest["recording_sha256"]
)
source_hash_matches = {}
for name in ("report.py", "judge.py", "runner.py"):
    source_hash_matches[name] = (
        hashlib.sha256(read_bytes("src/mcp_eval/" + name)).hexdigest() == manifest["engine_sources"][name]
    )
checks["three_consulted_source_hashes_match_manifest"] = all(source_hash_matches.values())
checks["read_inputs_unchanged_during_check"] = all((root / path).read_bytes() == data for path, data in inputs.items())

totals = Counter(by_id[item_id]["verdict"] for item_id in plan_ids)
planned_count = len(plan)
judged_count = totals["pass"] + totals["fail"]
output = {
    "scope": "offline_saved_report_accounting_only; no product imports, replay, device or API execution",
    "cwd": str(root), "executable": sys.executable, "python_version": sys.version.split()[0],
    "run_id": manifest["run_id"],
    "totals": {
        "planned": planned_count, "result_rows": len(records),
        **{verdict: totals[verdict] for verdict in ("pass", "fail", "unassessed")},
        "pass_rate_planned": totals["pass"] / planned_count,
        "judge_coverage": judged_count / planned_count,
        "pass_rate_judged": totals["pass"] / judged_count if judged_count else None,
        "execution_status_counts": dict(Counter(record["execution_status"] for record in records)),
        "source_type_counts": dict(Counter(record["source_type"] for record in records)),
        "level_counts": dict(Counter(item["level"] for item in plan)),
        "non_null_model_count": sum(record.get("model") is not None for record in records),
        "latency_sample_count": sum(record.get("latency_ms") is not None for record in records),
        "missing_result_ids": sorted(set(plan_ids) - set(result_ids)),
        "unplanned_result_ids": sorted(set(result_ids) - set(plan_ids)),
    },
    "manifest_status_fields": {key: manifest.get(key) for key in ("state", "recorded_items", "attempted_items")},
    "computed_summary": computed_summary,
    "items": item_details,
    "recording_input_event_count": len(recording),
    "recording_to_saved_result_differences": recording_differences,
    "artifact_matches": artifact_matches,
    "consulted_source_hash_matches": source_hash_matches,
    "checks": checks,
    "input_files": {path: {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()} for path, data in sorted(inputs.items())},
    "exit_status": 0 if all(checks.values()) else 1,
}
print(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False))
raise SystemExit(output["exit_status"])
