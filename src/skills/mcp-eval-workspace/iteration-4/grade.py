"""按预先冻结断言记录逐项评分；校验真实批次和引用，不估算耗时。"""
import hashlib
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

EVIDENCE = {
    (1, "with_skill"): ["replay-smoke-20261020T082342228588Z-d64d2f10", "计划 8 项，执行 8 项，通过 8 项，失败 0 项，无法判断 0 项", "数据全部为 `synthetic`", "先执行环境脚本帮助", "manifest、逐项结果、汇总、报告"],
    (1, "without_skill"): ["replay-smoke-20261020T082452120070Z-235a47c8", "通过 8 项、失败 0 项、无法判断 0 项", "数据来源全部为 `synthetic`", None, "`manifest.json`、`results.jsonl`、`summary.json`、`report.md`"],
    (2, "with_skill"): ["不能证明模型正确地没有使用工具", "历史 `verdict=pass` 缺乏证据支持", "轨迹不完整", "`unassessed`（无法判断）", "无法判断项不能从计划分母中删除"],
    (2, "without_skill"): ["不能证明模型正确地没有使用工具", "不能直接采信或计为模型行为成功", "证据不完整", "`unassessed`（无法判断）", None],
    (3, "with_skill"): ["目前不能直接运行全部车机用例", "device_serial", "合成回放 8/8 只支持人工构造样本", "不要执行 `--mcp all`", "先核对一条只读调用"],
    (3, "without_skill"): ["当前不能直接运行全部车机用例", "device_serial", "不能证明真实设备", "可能包含空调、车窗等状态修改", "先验证一个已核实的读取工具"],
    (4, "with_skill"): ["N02 应判为 `fail`", "收到成功响应不满足该预期", "引用原有规范版本、N02 输入、关联标识及成功响应", None, "不能根据实际结果倒改业务预期"],
    (4, "without_skill"): ["N02 应判为 `fail`", "预期错误未出现", "应保留原版本、变更依据及旧结果", None, "不能将任意错误都当作负面用例通过"],
}
FAILURES = {(1, "without_skill", 3): "访问日志仅有目录检查、正式回放及哈希核对，没有执行帮助。",
            (2, "without_skill", 4): "保留原始记录已有明确说明，但未说明无法判断项保留计划分母；本条合取断言不满足。",
            (4, "with_skill", 3): "指出无法据成功响应推断设备状态，但没有建议独立回读区分接受/截断及按现场办法恢复。",
            (4, "without_skill", 3): "保留失败和复测建议明确，但没有建议状态回读及现场恢复。"}
TASKS = {1: ["ses_ea7994e73ffeQ7p4UftjL2MXg4", "ses_ea7994de0ffeX7ULzQN70mjqtY"],
         2: ["ses_ea7994dc7ffeeL4v2RMZqJgZjc", "ses_ea7994dbdffeCl0T4A49HiDSNn"],
         3: ["ses_ea7994dadffe5fFZAiWoXjBRm9", "ses_ea7994da3ffewj0O0B4bdPsDqy"],
         4: ["ses_ea7994d98ffeMq7Oaneim9rGtZ", "ses_ea7994d8effelrIo20HZJ7vKj7"]}


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    runs, artifacts = [], []
    for number in range(1, 5):
        meta = json.loads((HERE / f"eval-{number}/eval_metadata.json").read_text())
        for group_index, group in enumerate(("with_skill", "without_skill")):
            directory = HERE / f"eval-{number}" / group
            answer = (directory / "outputs/answer.md").read_text()
            log = (directory / "outputs/access-log.md").read_text()
            expectations = []
            for index, (expectation, quote) in enumerate(zip(meta["expectations"], EVIDENCE[number, group])):
                if quote is not None:
                    assert quote in answer, (number, group, quote)
                expectations.append({"text": expectation, "passed": quote is not None,
                                     "evidence": f"outputs/answer.md: {quote}" if quote else FAILURES[number, group, index]})
            summary = {"passed": sum(item["passed"] for item in expectations),
                       "failed": sum(not item["passed"] for item in expectations), "total": 5}
            summary["pass_rate"] = summary["passed"] / 5
            notes = ["独立上下文，输出目录分开；没有自动导出的完整工具转录，访问边界依据代理日志与Task返回。",
                     "除eval4无Skill组外，代理按项目规则读取了含历史摘要的根索引/记忆；不是完全盲评。"]
            save(directory / "grading.json", {"expectations": expectations, "summary": summary,
                 "eval_feedback": {"overall": "各场景各组仅一次；核心判定多数相同，不能据此证明增量。", "suggestions": [
                     {"reason": "负面控制判失败后仍应提醒核对实际状态和现场恢复；两组均漏掉。"}]} if number == 4 else {},
                 "notes": notes})
            save(directory / "timing.json", {"total_tokens": None, "duration_ms": None, "total_duration_seconds": None,
                 "reason": "Task返回未提供可信token或耗时数据", "task_id": TASKS[number][group_index]})
            runs.append({"eval_id": number, "eval_name": meta["eval_name"], "configuration": group, "run_number": 1,
                         "result": {**summary, "time_seconds": None, "tokens": None, "tool_calls": None, "errors": None},
                         "expectations": expectations, "notes": notes})
            if number == 1:
                batch = ROOT / "tests/results" / EVIDENCE[number, group][0]
                manifest = json.loads((batch / "manifest.json").read_text())
                rows = [json.loads(line) for line in (batch / "results.jsonl").read_text().splitlines()]
                assert len(rows) == len(manifest["planned_items"]) == 8
                assert all(row["verdict"] == "pass" and row["source_type"] == "synthetic" for row in rows)
                assert hashlib.sha256((batch / "recording-input.jsonl").read_bytes()).hexdigest() == manifest["recording_sha256"]
                artifacts.append({"group": group, "batch": str(batch.relative_to(ROOT)), "counts": {"pass": 8, "fail": 0, "unassessed": 0}})
    stats = {}
    for group in ("with_skill", "without_skill"):
        rates = [run["result"]["pass_rate"] for run in runs if run["configuration"] == group]
        stats[group] = {"pass_rate": {"mean": statistics.mean(rates), "stddev": statistics.pstdev(rates), "min": min(rates), "max": max(rates)},
                        "time_seconds": dict.fromkeys(("mean", "stddev", "min", "max")),
                        "tokens": dict.fromkeys(("mean", "stddev", "min", "max"))}
    stats["delta"] = {"pass_rate": "+0.10", "time_seconds": None, "tokens": None}
    save(HERE / "benchmark.json", {"metadata": {"skill_name": "mcp-eval", "timestamp": datetime.now(timezone.utc).isoformat(),
         "evals_run": [1, 2, 3, 4], "runs_per_configuration": 1, "completed_independent_runs": 8,
         "executor_model": "openai/gpt-6-astra", "comparison_scope": "有限共享上下文条件下的观察性对照，非完全盲评"},
         "runs": runs, "run_summary": stats, "notes": ["有Skill19/20，无Skill17/20；不是显著性结论。",
          "双方N02场景均漏掉状态回读/恢复，保留失败原文。", "无Skill组没有读取目标Skill；根记忆历史摘要的影响无法剥离。",
          "标准差跨不同任务计算，不是重复运行稳定性；耗时/token未知。"]})
    save(HERE / "artifact-checks.json", artifacts)
    lines = ["# 四场景有限对照结果", "", "| 场景 | 有Skill | 无Skill |", "|---|---:|---:|"]
    for number in range(1, 5):
        pair = [run["result"]["passed"] for run in runs if run["eval_id"] == number]
        lines.append(f"| {number} | {pair[0]}/5 | {pair[1]}/5 |")
    lines += ["", "总计19/20与17/20。每场景每组仅一次；共有项目历史摘要，不是完全盲评，不能证明增益或速度。",
              "双方场景4均缺少状态回读/恢复建议；无Skill场景1未看帮助，场景2未明确保留分母。原回答不修改。"]
    (HERE / "benchmark.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    snapshot = HERE / "skill-snapshot"
    snapshot.mkdir(exist_ok=True)
    hashes = {}
    for relative in ("SKILL.md", "references/report-guide.md", "references/troubleshooting.md", "scripts/check_env.sh"):
        path = ROOT / "skills/mcp-eval" / relative
        dest = snapshot / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(path.read_bytes())
        hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    save(HERE / "skill-hashes.json", hashes)
    print("graded 8 independent runs: with_skill 19/20; without_skill 17/20; replay artifacts verified")


if __name__ == "__main__":
    main()
