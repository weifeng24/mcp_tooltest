"""冻结Skill评测输入并建立互不写入的执行副本；不连接设备/模型。"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from mcp_eval.judge import judge_record
from mcp_eval.records import EvalRecord, read_jsonl
from mcp_eval.report import write_report
from mcp_eval.runner import run_evaluation

HERE = Path(__file__).resolve().parent / "iteration-6"


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def hashes(path):
    return {str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(path.rglob("*")) if p.is_file() and "__pycache__" not in p.parts}


def main():
    HERE.mkdir(exist_ok=False)
    skill = ROOT / "skills/mcp-eval"
    shutil.copytree(skill, HERE / "skill-snapshot")
    save(HERE / "skill-hashes.json", hashes(skill))
    save(HERE / "engine-hashes.json", hashes(ROOT / "src/mcp_eval"))
    evals = json.loads((skill / "evals/evals.json").read_text())
    save(HERE / "evals-frozen.json", evals)
    outcome = run_evaluation("configs/runs/replay_smoke.json", ROOT)
    source_batch = Path(outcome["manifest"]).parent
    fixture_batch = HERE / "input-snapshot/fixtures/report-batch"
    shutil.copytree(source_batch, fixture_batch)
    manifest = json.loads((fixture_batch / "manifest.json").read_text())
    cases = {c["case_id"]: c for c in manifest["inputs"]["cases"]}
    rows = []
    for raw in read_jsonl(fixture_batch / "results.jsonl"):
        record = EvalRecord.from_dict(raw)
        record.source_type = "synthetic"
        record.provenance["skill_eval_fixture"] = "manually_constructed_mixed_outcomes_not_device_evidence"
        if record.case_id == "N02":
            record.response_raw = {"jsonrpc": "2.0", "id": 1, "result": {"isError": False, "success": True}}
        if record.case_id == "P05":
            record.execution_status, record.trace_complete = "not_run", False
            record.response_raw, record.error_category = None, "fixture_missing_evidence"
        judge_record(cases[record.case_id], record)
        rows.append(record.to_dict())
        if record.evidence:
            save(fixture_batch / record.evidence[0], record.to_dict())
    (fixture_batch / "results.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))
    write_report(fixture_batch / "results.jsonl", cases, fixture_batch, manifest["run_id"], manifest["planned_items"])
    shutil.copytree(fixture_batch, HERE / "input-snapshot/fixtures/rebuild-batch")
    save(HERE / "input-snapshot/fixtures/rebuild-batch/summary.json", {"stale": True, "total": 999})
    (HERE / "input-snapshot/fixtures/rebuild-batch/report.md").write_text("# STALE：请从冻结批次重建\n")
    save(HERE / "input-snapshot/fixtures/anomaly.json", {
        "source_type": "synthetic", "purpose": "规范与响应冲突的离线情景，非真实车机缺陷",
        "tool_version": "fixture-v1", "spec_version": "frozen-fixture-2026-10-23",
        "allowed_temperature": [16, 30], "case": cases["N02"],
        "request": {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "HvacService.setTemp", "arguments": {"temperature": 40}}},
        "response": {"jsonrpc": "2.0", "id": 1, "result": {"isError": False, "success": True}},
        "independent_state_readback": None, "recovery_method": "未在真实设备确认"})
    save(HERE / "input-snapshot/fixtures/missing-evidence.json", {
        "source_type": "synthetic", "case_id": "M03", "execution_status": "error", "error_category": "provider_error",
        "trace_complete": False, "response_raw": {"tool_calls": []}, "verdict": "pass",
        "fixture_note": "故意保留旧错误判定，用于检查证据解释；不得改写此输入"})
    save(HERE / "input-hashes.json", hashes(HERE / "input-snapshot"))
    for case in evals["evals"]:
        folder = HERE / f"eval-{case['id']}-{case['name']}"
        save(folder / "eval_metadata.json", {"eval_id": case["id"], "eval_name": case["name"], "category": case["category"],
                                             "prompt": case["prompt"], "assertions": case["expectations"]})
        for mode in ("with_skill", "without_skill"):
            run = folder / mode
            (run / "outputs").mkdir(parents=True)
            sandbox = run / "sandbox"
            sandbox.mkdir()
            for name in ("src/mcp_eval", "configs", "tests/cases", "recordings"):
                shutil.copytree(ROOT / name, sandbox / name, ignore=shutil.ignore_patterns("__pycache__"))
            for name in ("README.md", "requirements.txt"):
                shutil.copy2(ROOT / name, sandbox / name)
            for name in ("device-readiness.md", "catalog-capture.md"):
                (sandbox / "docs").mkdir(exist_ok=True)
                shutil.copy2(ROOT / "docs" / name, sandbox / "docs" / name)
            shutil.copytree(HERE / "input-snapshot/fixtures", sandbox / "fixtures")
            if mode == "with_skill":
                shutil.copytree(HERE / "skill-snapshot", sandbox / "skills/mcp-eval")
            save(run / "input-hashes-before.json", hashes(sandbox / "fixtures"))
            save(run / "timing.json", {"total_tokens": None, "duration_ms": None, "total_duration_seconds": None,
                                       "reason": "等待工具实际返回，缺字段不估算"})
    save(HERE / "execution-contract.json", {
        "created_at": datetime.now(timezone.utc).isoformat(), "conditions": ["with_skill", "without_skill"],
        "positive_cases": 5, "negative_cases": 2, "runs_per_configuration": 1,
        "skill_runtime_changed": False, "comparison": "stable_skill_coverage_expansion_vs_no_target_skill",
        "isolation": "separate_writable_copies_no_OS_sandbox_shared_history_possible",
        "real_device_or_model_api": False, "bootstrap_smoke": outcome})
    print(json.dumps({"workspace": str(HERE), "cases": len(evals["evals"]), "execution_copies": 14}, ensure_ascii=False))


if __name__ == "__main__":
    main()
