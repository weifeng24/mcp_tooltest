"""Verify this batch's saved evidence without importing the evaluation engine."""

import json
from collections import Counter
from pathlib import Path


def load_json(path):
    return path.read_text(encoding="utf-8")


def load_hashes(path):
    return {
        name: digest
        for digest, name in (
            line.split("  ", 1) for line in path.read_text(encoding="utf-8").splitlines()
        )
    }


batch = Path("fixtures/rebuild-batch")
output = Path("../outputs")
manifest = json.loads(load_json(batch / "manifest.json"))
records = [
    json.loads(line)
    for line in load_json(batch / "results.jsonl").splitlines()
    if line.strip()
]
summary = json.loads(load_json(batch / "summary.json"))
report = load_json(batch / "report.md")
before = load_hashes(output / "01-immutable-before.sha256")
after = load_hashes(output / "08-immutable-after.sha256")
reports_before = load_hashes(output / "02-reports-before.sha256")
reports_after = load_hashes(output / "09-reports-after.sha256")
assert before == after, "Immutable file hashes changed"
assert set(reports_before) == set(reports_after)
assert all(reports_before[name] != reports_after[name] for name in reports_before)

provided = json.loads(load_json(Path("../input-hashes-before.json")))
for name, digest in {**before, **reports_before}.items():
    if name.startswith("fixtures/rebuild-batch/"):
        assert digest == provided[name.removeprefix("fixtures/")], name
assert before[str(batch / "recording-input.jsonl")] == manifest["recording_sha256"]
for name, digest in manifest["engine_sources"].items():
    assert before[f"src/mcp_eval/{name}"] == digest, name

plan = manifest["planned_items"]
by_id = {row["item_id"]: row for row in records}
assert len(by_id) == len(records) == len(plan)
assert set(by_id) == {item["item_id"] for item in plan}
assert summary["total"] == len(plan)
assert summary["observed"] == len(records)
assert summary["run_id"] == manifest["run_id"]
cases = {case["case_id"]: case for case in manifest["inputs"]["cases"]}
expected_groups = {}
for item in plan:
    row = by_id[item["item_id"]]
    assert row["run_id"] == manifest["run_id"]
    for key in ("case_id", "channel", "action", "model", "repeat_index"):
        assert row[key] == item[key], (item["item_id"], key)
    case = cases[item["case_id"]]
    assert case["level"] == item["level"]
    assert case["category"] == item["category"]
    artifact = batch / "artifacts" / f'{item["item_id"]}.json'
    assert json.loads(load_json(artifact)) == row, str(artifact)
    assert f'| {item["item_id"]} | {item["case_id"]} |' in report
    assert f'| {row["execution_status"]} | {row["verdict"]} |' in report
    key = "|".join((item["channel"], item["level"], item["category"], item["model"] or "-"))
    group = expected_groups.setdefault(key, Counter())
    group["planned"] += 1
    group[row["verdict"]] += 1

assert set(expected_groups) == set(summary["groups"])
for key, expected in expected_groups.items():
    actual = summary["groups"][key]
    for field in ("planned", "pass", "fail", "unassessed"):
        assert actual[field] == expected[field], (key, field)
    assert actual["pass_rate_planned"] == expected["pass"] / expected["planned"]
    assert actual["judge_coverage"] == (expected["pass"] + expected["fail"]) / expected["planned"]

counts = Counter(row["verdict"] for row in records)
attempted = sum(row["execution_status"] != "not_run" for row in records)
not_run = [row["case_id"] for row in records if row["execution_status"] == "not_run"]
stderr_sizes = {
    path.name: path.stat().st_size
    for path in output.glob("*.stderr.txt")
    if path.name != "11-verify.stderr.txt"
}
assert all(size == 0 for size in stderr_sizes.values()), stderr_sizes
print(json.dumps({
    "verification": "passed",
    "run_id": manifest["run_id"],
    "immutable_files_unchanged": len(before),
    "batch_input_files_unchanged": sum(name.startswith("fixtures/rebuild-batch/") for name in before),
    "provided_batch_before_hashes_match": True,
    "recording_matches_manifest_hash": True,
    "engine_sources_matching_manifest": len(manifest["engine_sources"]),
    "artifacts_equal_results": len(records),
    "summary_matches_frozen_plan_and_results": True,
    "planned": len(plan),
    "observed": len(records),
    "counts": dict(counts),
    "pass_rate_planned": counts["pass"] / len(plan),
    "judge_coverage": (counts["pass"] + counts["fail"]) / len(plan),
    "pass_rate_judged": counts["pass"] / (counts["pass"] + counts["fail"]),
    "execution_status_counts": dict(Counter(row["execution_status"] for row in records)),
    "not_run_cases": not_run,
    "result_attempted_items": attempted,
    "manifest_attempted_items": manifest.get("attempted_items"),
    "attempted_metadata_consistent": manifest.get("attempted_items") == attempted,
    "source_types": sorted({row["source_type"] for row in records}),
    "fixture_provenance": sorted({row["provenance"]["skill_eval_fixture"] for row in records}),
    "known_latency_samples": sum(row["latency_ms"] is not None for row in records),
    "report_hash_changes": {
        name: {"before": reports_before[name], "after": reports_after[name]}
        for name in reports_before
    },
    "completed_command_stderr_bytes": stderr_sizes,
    "total_tokens": None,
    "total_duration_seconds": None,
}, ensure_ascii=False, indent=2))
