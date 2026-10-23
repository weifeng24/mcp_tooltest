"""本组一次性报告重建与完整性核验；不修改产品源码或冻结输入。"""
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path.cwd().resolve()
OUT = ROOT.parent / "outputs"
BATCH = ROOT / "fixtures/rebuild-batch"
PREFIX = "fixtures/rebuild-batch/"
MUTABLE = {PREFIX + "summary.json", PREFIX + "report.md"}
# 清单来自本组 Glob 的实际结果；不遍历其他 fixture、历史目录或 Skill。
SOURCE_NAMES = [
    "__init__.py", "__main__.py", "catalog.py", "config.py", "device.py",
    "judge.py", "model_loop.py", "providers/__init__.py", "providers/base.py",
    "providers/openai_compat.py", "records.py", "replay.py", "report.py", "runner.py",
]
CONFIG_NAMES = [
    "models/deepseek.json", "models/kimi.json", "runs/l1_device.json",
    "runs/l2_device.json", "runs/replay_smoke.json", "servers/ark_mcp_service.json",
]
FILES = sorted(
    ["README.md", "requirements.txt"]
    + ["src/mcp_eval/" + name for name in SOURCE_NAMES]
    + ["configs/" + name for name in CONFIG_NAMES]
    + [PREFIX + name for name in (
        "manifest.json", "results.jsonl", "recording-input.jsonl", "summary.json", "report.md"
    )]
    + [PREFIX + f"artifacts/item-{index:05d}.json" for index in range(1, 9)]
)


def save(name, value):
    # 保留本次原始证据，拒绝覆盖已有输出。
    with (OUT / name).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def snapshot():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in FILES}


assert ROOT.name == "sandbox" and ROOT.parent.name == "without_skill"
assert os.environ["PYTHONPATH"] == "src"
assert os.environ["PYTHONDONTWRITEBYTECODE"] == "1"
before = snapshot()
save("hashes-before.json", {"algorithm": "sha256", "root": str(ROOT), "files": before})
baseline = json.loads((ROOT.parent / "input-hashes-before.json").read_text(encoding="utf-8"))
batch_baseline = {"fixtures/" + key: value for key, value in baseline.items()
                  if key.startswith("rebuild-batch/")}
baseline_mismatches = [name for name, value in batch_baseline.items() if before.get(name) != value]
save("baseline-check.json", {"scope": "rebuild-batch only", "checked": len(batch_baseline),
                             "mismatches": baseline_mismatches})
assert len(batch_baseline) == 13 and not baseline_mismatches, "冻结批次与提供的原始哈希不一致"

argv = [sys.executable, "-B", "-m", "mcp_eval", "rebuild", "fixtures/rebuild-batch"]
with (OUT / "rebuild.stdout.txt").open("xb") as stdout, (OUT / "rebuild.stderr.txt").open("xb") as stderr:
    process = subprocess.run(argv, cwd=ROOT, stdout=stdout, stderr=stderr, check=False)
save("rebuild-command.json", {
    "argv": argv, "cwd": str(ROOT), "environment_overrides": {
        "PYTHONPATH": "src", "PYTHONDONTWRITEBYTECODE": "1"
    }, "returncode": process.returncode,
    "stdout": "rebuild.stdout.txt", "stderr": "rebuild.stderr.txt",
})
after = snapshot()
save("hashes-after.json", {"algorithm": "sha256", "root": str(ROOT), "files": after})
changed = [name for name in FILES if before[name] != after[name]]
unexpected = [name for name in changed if name not in MUTABLE]
save("hash-comparison.json", {
    "checked_files": len(FILES), "changed": changed, "unexpected_changes": unexpected,
    "immutable_files": len(FILES) - len(MUTABLE),
    "immutable_unchanged": not unexpected,
    "original_batch_immutable_match": all(after[name] == value for name, value in batch_baseline.items()
                                          if name not in MUTABLE),
})
assert process.returncode == 0, "重建命令失败，查看原始 stdout/stderr"
assert set(changed) == MUTABLE and not unexpected, "变更范围不符"

manifest = json.loads((BATCH / "manifest.json").read_text(encoding="utf-8"))
results = [json.loads(line) for line in (BATCH / "results.jsonl").read_text(encoding="utf-8").splitlines()
           if line.strip()]
summary = json.loads((BATCH / "summary.json").read_text(encoding="utf-8"))
report = (BATCH / "report.md").read_text(encoding="utf-8")
planned = manifest["planned_items"]
cases = {case["case_id"]: case for case in manifest["inputs"]["cases"]}
by_id = {record["item_id"]: record for record in results}
assert len(by_id) == len(results) == len(planned)
assert set(by_id) == {item["item_id"] for item in planned}
assert summary["run_id"] == manifest["run_id"]
assert summary["total"] == len(planned) and summary["observed"] == len(results)
assert "stale" not in summary and "STALE" not in report

groups = {}
for item in planned:
    record = by_id[item["item_id"]]
    assert (record["case_id"], record["model"], record["channel"], record["repeat_index"]) == (
        item["case_id"], item["model"], item["channel"], item["repeat_index"])
    artifact = json.loads((BATCH / "artifacts" / f"{item['item_id']}.json").read_text(encoding="utf-8"))
    assert artifact == record, f"artifact 与 results 不一致: {item['item_id']}"
    case = cases[item["case_id"]]
    key = "|".join([item["channel"], case["level"], case["category"], item["model"] or "-"])
    groups.setdefault(key, []).append(record)
    row = [line for line in report.splitlines() if line.startswith(f"| {item['item_id']} |")]
    assert len(row) == 1
    for value in (record["case_id"], record["execution_status"], record["verdict"], record["verdict_reason"]):
        assert f"| {value} |" in row[0]
    assert f"artifacts/{item['item_id']}.json" in row[0]

assert set(groups) == set(summary["groups"])
for key, records in groups.items():
    counts = Counter(record["verdict"] for record in records)
    actual = summary["groups"][key]
    total = len(records)
    judged = counts["pass"] + counts["fail"]
    assert actual["planned"] == total
    assert all(actual[name] == counts[name] for name in ("pass", "fail", "unassessed"))
    assert actual["pass_rate_planned"] == counts["pass"] / total
    assert actual["judge_coverage"] == judged / total
    assert actual["pass_rate_judged"] == counts["pass"] / judged
    assert actual["source_types"] == sorted({record["source_type"] for record in records})
    assert all(record["latency_ms"] is None for record in records)
    assert actual["latency_ms"] == {"median": None, "min": None, "max": None, "samples": 0}
    assert all(value == actual["latency_ms"] for value in actual["latency_by_verdict"].values())
    escaped = key.replace("|", "\\|")
    assert (f"| {escaped} | {total} | {counts['pass']} | {counts['fail']} | {counts['unassessed']} | "
            f"{counts['pass'] / total:.1%} | {judged / total:.1%} |") in report

failures = Counter(record["error_category"] or "assertion_failed" for record in results
                   if record["verdict"] == "fail")
assert summary["failure_categories"] == dict(failures)
assert "synthetic" in report and "合成数据不能支撑真机结论" in report
engine_mismatches = [name for name, value in manifest["engine_sources"].items()
                     if before.get("src/mcp_eval/" + name) != value]
recording_matches = after[PREFIX + "recording-input.jsonl"] == manifest["recording_sha256"]
assert not engine_mismatches and recording_matches
counts = Counter(record["verdict"] for record in results)
verification = {
    "status": "passed", "planned": len(planned), "observed": len(results), "counts": dict(counts),
    "pass_rate_planned": counts["pass"] / len(planned),
    "judge_coverage": (counts["pass"] + counts["fail"]) / len(planned),
    "pass_rate_judged": counts["pass"] / (counts["pass"] + counts["fail"]),
    "execution_status_counts": dict(Counter(record["execution_status"] for record in results)),
    "source_types": sorted({record["source_type"] for record in results}),
    "failure_categories": dict(failures), "artifacts_match_results": len(results),
    "recording_matches_manifest": recording_matches, "engine_source_mismatches": engine_mismatches,
    "hash_checked_files": len(FILES), "changed_files": changed,
    "immutable_files_unchanged": len(FILES) - len(MUTABLE),
    "report_item_rows_checked": len(planned), "summary_groups_checked": len(groups),
    "tool_or_model_rerun": False,
    "method": "rebuild CLI; independent JSON/count/report/hash checks; no run command or rejudging",
}
save("verification.json", verification)
print(json.dumps(verification, ensure_ascii=False, indent=2))
