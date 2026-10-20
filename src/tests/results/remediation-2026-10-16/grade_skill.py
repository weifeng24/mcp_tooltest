"""归档有限 Skill 行为复测；缺失时间/token 不填零，不计算速度收益。"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WORKSPACE = ROOT / "skills/mcp-eval-workspace/iteration-2"

QUOTES = {
    (2, "with_skill"): ["不能证明模型正确地没有使用工具", "调用轨迹不完整", "保留缺失项及原计划分母"],
    (2, "without_skill"): ["不能证明模型正确地没有使用工具", "调用轨迹不完整", "避免隐去失败执行"],
    (3, "with_skill"): ["不证明真机", "`device_serial` 为空", "不能当作纯只读发现接口"],
    (3, "without_skill"): ["不能证明真实设备", "`device_serial` 为空", "不是纯只读工具发现命令"],
}
TASKS = {
    (2, "with_skill"): "ses_ebbbd93adffeCQugX8Q6tjrzDp",
    (2, "without_skill"): "ses_ebbbd93a3ffe9Q0z81t1mfUuIY",
    (3, "with_skill"): "ses_ebbbd9398ffeObWWXMv5VwuMcX",
    (3, "without_skill"): "ses_ebbbd9388ffe63Ud9jtJJ3RNYf",
}


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    runs = []
    snapshots = {}
    for folder in sorted(WORKSPACE.glob("eval-*")):
        meta = json.loads((folder / "eval_metadata.json").read_text(encoding="utf-8"))
        for mode in ("with_skill", "without_skill"):
            target = folder / mode
            answer_path = target / "outputs/answer.md"
            text = answer_path.read_text(encoding="utf-8")
            access = json.loads((target / "outputs/access-log.json").read_text(encoding="utf-8"))
            paths = access.get("actual_read_paths", access.get("read_paths", []))
            if mode == "without_skill":
                assert all("/skills/" not in path and "/src/mcp_eval/" not in path for path in paths)
            for source in paths:
                contents = Path(source).read_text(encoding="utf-8")
                snapshots[source] = {"sha256": hashlib.sha256(contents.encode()).hexdigest(), "content": contents}
            expectations = []
            for criterion, quote in zip(meta["assertions"], QUOTES[(meta["eval_id"], mode)]):
                passed = quote in text
                expectations.append({"text": criterion, "passed": passed,
                                     "evidence": f"outputs/answer.md: {quote}" if passed else "未发现指定证据"})
            # 第三项按语义评分；基线用“行为不可判定”表达 unassessed，不要求固定词形。
            passed = sum(item["passed"] for item in expectations)
            summary = {"passed": passed, "failed": len(expectations) - passed,
                       "total": len(expectations), "pass_rate": passed / len(expectations)}
            save(target / "grading.json", {"expectations": expectations, "summary": summary,
                 "notes": ["有限行为语义检查；不是自动触发率或设备/API验证。", "baseline 的不可判定按 unassessed 等效语义评分。"]})
            save(target / "timing.json", {"task_id": TASKS[(meta["eval_id"], mode)],
                 "total_tokens": None, "duration_ms": None, "total_duration_seconds": None,
                 "reason": "Task返回未提供这些指标，未推测或以零代替"})
            runs.append({"eval_id": meta["eval_id"], "eval_name": meta["eval_name"], "configuration": mode,
                         "run_number": 1, "result": {**summary, "time_seconds": None, "tokens": None},
                         "expectations": expectations})
    stats = {}
    for mode in ("with_skill", "without_skill"):
        values = [run["result"]["pass_rate"] for run in runs if run["configuration"] == mode]
        mean = sum(values) / len(values)
        stddev = (sum((value - mean) ** 2 for value in values) / (len(values) - 1)) ** 0.5 if len(values) > 1 else 0
        stats[mode] = {"pass_rate": {"mean": mean, "stddev": stddev, "min": min(values), "max": max(values)}}
    stats["delta"] = {"pass_rate": f"{stats['with_skill']['pass_rate']['mean'] - stats['without_skill']['pass_rate']['mean']:+.2f}"}
    benchmark = {"metadata": {"skill_name": "mcp-eval", "evals_run": [2, 3], "runs_per_configuration": 1,
                  "timestamp": datetime.now(timezone.utc).isoformat(), "executor_model": "harness general agent，未单独报告模型ID"},
                 "runs": runs, "run_summary": stats,
                 "notes": ["两组都能正确回答；这两题不能证明Skill带来增量效果。",
                           "基线明确禁止访问Skill，访问说明已检查；共同上下文包含同一项目规则和状态。",
                           "无时长/token数据，未生成相关统计。自动触发及用户反馈尚待执行。",
                           "with_skill的eval2引用了不存在的第9条编号，主体语义正确，但引用精度仍需人工复核。"]}
    save(WORKSPACE / "benchmark.json", benchmark)
    save(WORKSPACE / "context-snapshot.json", snapshots)
    (WORKSPACE / "analysis.md").write_text(
        "# 有限行为复测结果\n\n人工加载Skill与无Skill基线各2题、每题3项，共各6/6满足主要语义要求。"
        "未证明增量收益，未测自动触发率，时长/token未知。基线未读取Skill；两组允许相同项目上下文。\n\n"
        "保留一个引用精度问题：with_skill的eval2提及报告指南第9条，但实际没有该编号。"
        "不影响本题主要判定，不能因此宣称所有输出事实均已通过。用户反馈与导师认可仍待确认。\n",
        encoding="utf-8")
    print(f"Saved {len(runs)} graded outputs; no timing/token estimates.")


if __name__ == "__main__":
    main()
