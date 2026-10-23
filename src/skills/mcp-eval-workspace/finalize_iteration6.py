"""检查已执行Skill证据，汇总独立评分；不执行模型或改写原回答。"""
import hashlib
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent / "iteration-6"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def hashes(path):
    return {str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(path.rglob("*")) if p.is_file() and "__pycache__" not in p.parts}


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def main():
    assert hashes(ROOT / "skills/mcp-eval") == load(HERE / "skill-hashes.json")
    assert hashes(ROOT / "src/mcp_eval") == load(HERE / "engine-hashes.json")
    assert load(ROOT / "configs/servers/ark_mcp_service.json")["device_serial"] == ""
    evals = load(HERE / "evals-frozen.json")["evals"]
    receipts = load(HERE / "task-receipts.json")
    assert len(receipts["runs"]) == 14 and all(r["state"] == "completed" for r in receipts["runs"])
    runs, checks, evidence_hashes, extra_batches = [], [], {}, []
    for case in evals:
        for mode in ("with_skill", "without_skill"):
            run = HERE / f"eval-{case['id']}-{case['name']}" / mode
            grade = load(run / "grading.json")
            assert [e["text"] for e in grade["expectations"]] == case["expectations"]
            assert len(grade["expectations"]) == 5
            p = sum(e["passed"] is True for e in grade["expectations"])
            assert grade["summary"]["passed"] == p and grade["summary"]["total"] == 5
            assert (run / "outputs/answer.md").is_file()
            assert (run / "access-log.md").is_file() or (run / "outputs/access-log.md").is_file()
            before, after = load(run / "input-hashes-before.json"), hashes(run / "sandbox/fixtures")
            permitted = {"rebuild-batch/summary.json", "rebuild-batch/report.md"} if case["id"] == 6 else set()
            changes = {name for name in before if before[name] != after.get(name)}
            assert changes <= permitted, (case["id"], mode, changes)
            assert hashes(run / "sandbox/src/mcp_eval") == load(HERE / "engine-hashes.json")
            if case["id"] == 1:
                batches = list((run / "sandbox/tests/results").glob("*/summary.json"))
                answer = (run / "outputs/answer.md").read_text()
                cited = [p for p in batches if p.parent.name in answer]
                assert len(cited) == 1
                extra_batches.extend({"configuration": mode, "path": str(p.parent.relative_to(HERE)),
                                      "status": "not_cited_by_answer_provenance_unresolved"}
                                     for p in batches if p not in cited)
                summary = load(cited[0])
                assert summary["total"] == 8 and sum(g["pass"] for g in summary["groups"].values()) == 8
            if case["id"] == 6:
                summary = load(run / "sandbox/fixtures/rebuild-batch/summary.json")
                assert summary["total"] == 8
                assert [sum(g[k] for g in summary["groups"].values()) for k in ("pass", "fail", "unassessed")] == [6, 1, 1]
            runs.append({"eval_id": case["id"], "eval_name": case["name"], "category": case["category"],
                         "configuration": mode, "run_number": 1,
                         "result": {"passed": p, "failed": 5 - p, "total": 5, "pass_rate": p / 5,
                                    "time_seconds": None, "tokens": None, "tool_calls": None, "errors": None},
                         "expectations": grade["expectations"], "notes": ["共享历史/通用Skill影响未剥离，非完全盲评；每组一次"]})
            checks.append({"eval_id": case["id"], "configuration": mode, "fixture_changes": sorted(changes),
                           "product_unchanged": True})
            evidence_hashes.update({str(run.relative_to(HERE) / "outputs" / name): value for name, value in hashes(run / "outputs").items()})
    summaries = {}
    for mode in ("with_skill", "without_skill"):
        values = [r["result"]["pass_rate"] for r in runs if r["configuration"] == mode]
        summaries[mode] = {"pass_rate": {"mean": statistics.mean(values), "stddev": statistics.stdev(values),
                                         "min": min(values), "max": max(values)},
                           "time_seconds": None, "tokens": None}
    summaries["delta"] = {"pass_rate": f"{summaries['with_skill']['pass_rate']['mean'] - summaries['without_skill']['pass_rate']['mean']:+.4f}",
                           "time_seconds": None, "tokens": None}
    benchmark = {"metadata": {"skill_name": "mcp-eval", "timestamp": datetime.now(timezone.utc).isoformat(),
                               "evals_run": [c["id"] for c in evals], "runs_per_configuration": 1,
                               "run_count_scope": "scored_outputs_not_total_execution_attempts",
                               "executor_model": "Task工具未报告worker模型；主会话openai/gpt-6-astra", "completed_independent_runs": 14},
                 "runs": runs, "run_summary": summaries,
                 "notes": ["有Skill35/35，无目标Skill32/35；7个任务各5条评分，不是35个独立用例。",
                           "基线两项未执行帮助，另有场景7序列号修改过程证据不足；该项不能解释为Skill的能力增益。",
                           "两组均读到根索引/记忆摘要及通用Skill，非盲评；标准差跨场景，不代表重复运行稳定性。",
                           "场景1两组各存在一个回答未引用的较早批次；评分只针对所引批次，额外执行来源尚未核实，不能声称每组仅执行一次。",
                           "未知token/耗时为null，未验证真实自动触发、业务效果或导师验收。"]}
    save(HERE / "benchmark.json", benchmark)
    save(HERE / "evidence-hashes.json", evidence_hashes)
    save(HERE / "artifact-checks.json", {"checks": checks, "skill_unchanged": True, "main_engine_unchanged": True,
                                         "main_device_serial_empty": True, "additional_batches": extra_batches,
                                         "known_process_gap": "baseline eval7 initial serial/write provenance not verified"})
    lines = ["# iteration-6行为评测汇总", "", "5正向＋2负面；同一Skill版本，每场景各配置选取一个明确引用的回答/批次评分，额外产物见限制。", "",
             "| 场景 | 分类 | 有Skill | 无目标Skill |", "|---|---|---:|---:|"]
    for case in evals:
        scores = [r["result"]["passed"] for r in runs if r["eval_id"] == case["id"]]
        lines.append(f"| {case['id']} {case['name']} | {case['category']} | {scores[0]}/5 | {scores[1]}/5 |")
    lines += ["", *["- " + note for note in benchmark["notes"]], "", "详细评分与证据：[grading-notes.md](grading-notes.md)。"]
    (HERE / "benchmark.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"runs": len(runs), "with_skill": sum(r["result"]["passed"] for r in runs if r["configuration"] == "with_skill"),
                      "without_skill": sum(r["result"]["passed"] for r in runs if r["configuration"] == "without_skill"),
                      "snapshots_unchanged": True}, ensure_ascii=False))


if __name__ == "__main__":
    main()
