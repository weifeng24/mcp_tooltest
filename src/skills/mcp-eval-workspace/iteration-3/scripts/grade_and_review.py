"""Grade retained fallback answers and generate the official static review.

Semantic verdicts are an inline main-context review, not an independent grader.
Machine checks verify citations, raw replay artifacts, hashes and output schemas.
"""
import hashlib
import json
from pathlib import Path
import re
import runpy
import sys
from datetime import datetime, timezone

from collect_evidence import ROOT, WORK, CREATOR, PYTHON, command, save

NULL_TIMING = {"total_tokens": None, "duration_ms": None, "total_duration_seconds": None}
NULL_STATS = {"mean": None, "stddev": None, "min": None, "max": None}


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def citations(answer):
    definitions = re.findall(r"^- 〔(\d+)〕 `([^`]+)`：(.+)$", answer, re.M)
    used = set(re.findall(r"〔(\d+)〕", answer.split("## 引用")[0]))
    defined = {number for number, _, _ in definitions}
    details = []
    for number, relative, explanation in definitions:
        path = ROOT / relative
        ok = path.is_file() and path.resolve().is_relative_to(ROOT)
        ranges = re.findall(r"第(\d+)(?:—(\d+))?行", explanation)
        if ok:
            size = len(path.read_text().splitlines())
            ok = all(1 <= int(start) <= int(end or start) <= size for start, end in ranges)
        details.append({"number": number, "path": relative, "valid": ok,
                        "sha256": digest(path) if path.is_file() else None})
    return {"valid": bool(used) and used == defined and len(defined) == len(definitions)
            and all(d["valid"] for d in details), "used": sorted(used), "references": details}


def replay_checks():
    event = load(WORK / "logs/replay-run.json")
    result = json.loads(event["stdout"])
    batch = Path(result["manifest"]).parent
    manifest = load(batch / "manifest.json")
    summary = load(batch / "summary.json")
    records = [json.loads(line) for line in (batch / "results.jsonl").read_text().splitlines()]
    artifacts = [load(batch / f"artifacts/{r['item_id']}.json") for r in records]
    planned = manifest["planned_items"]
    counts = {key: sum(r["verdict"] == key for r in records) for key in ("pass", "fail", "unassessed")}
    checks = {
        "output_path_inside_iteration": batch.resolve().is_relative_to(WORK),
        "uuid_requested_run_id": bool(re.fullmatch(r"skill-iteration3-[0-9a-f]{32}", manifest["requested_run_id"])),
        "four_files_exist": all((batch / name).is_file() for name in ("manifest.json", "results.jsonl", "summary.json", "report.md")),
        "run_ids_match": manifest["run_id"] == summary["run_id"] == result["run_id"] == batch.name
                         and all(r["run_id"] == batch.name for r in records),
        "all_planned_items_preserved": len(planned) == len(records) == summary["total"] == summary["observed"] == 8
                                      and {p["item_id"] for p in planned} == {r["item_id"] for r in records},
        "counts_match": counts == result["counts"] == {"pass": 8, "fail": 0, "unassessed": 0}
                        and all(sum(g[key] for g in summary["groups"].values()) == count for key, count in counts.items()),
        "all_completed_synthetic": all(r["source_type"] == "synthetic" and r["channel"] == "replay"
                                       and r["execution_status"] == "completed" for r in records),
        "all_artifacts_match": artifacts == records,
        "recording_hash_matches": digest(ROOT / manifest["inputs"]["run"]["recording"]) == manifest["recording_sha256"],
        "source_ids_match": all(r["provenance"]["source_run_id"] == "synthetic-v2" for r in records),
        "model_repeat_match": all(r["model"] is None and r["repeat_index"] == 0 for r in records),
        "command_succeeded": event["exit_code"] == 0,
    }
    copied = load(WORK / "inputs/replay.json")
    original = load(ROOT / "configs/runs/replay_smoke.json")
    checks["only_config_routing_changed"] = {k for k in copied.keys() | original.keys() if copied.get(k) != original.get(k)} == {"run_id", "output_dir"}
    evidence = {"batch": str(batch.relative_to(ROOT)), "checks": checks, "counts": counts,
                "planned": len(planned), "unexecuted": len(planned) - result["executed"],
                "case_ids": [r["case_id"] for r in records], "recording_sha256": manifest["recording_sha256"],
                "raw_artifact_hashes": {str(p.relative_to(WORK)): digest(p) for p in batch.rglob("*") if p.is_file()}}
    save("logs/replay-artifact-checks.json", evidence)
    return evidence


SEMANTIC_EVIDENCE = {
    1: [
        "先执行环境脚本帮助、环境检查、CLI 帮助和 run 帮助，再执行本轮配置的 `--dry-run` 与正式回放。",
        "skill-iteration3-ac0e7d639e7746ed83d2febac233b593-20261019T103235034082Z-a0470db4",
        "分母N=8来自 manifest 的全部 `planned_items`，并非仅统计成功结果。",
        "这验证本次合成回放，不证明真机、真实模型、IDE或自动触发通过，也不代表导师验收。",
        "本轮没有重新执行160项完整回归或7个原反例；相关完成事实来自用户最新说明。"],
    2: [
        "不能证明模型正确地没有用工具，原 `verdict=pass` 缺乏依据，应撤回该通过结论。",
        "`execution_status=error` 与 `error_category=provider_error` 表示模型提供方调用链路出错；`trace_complete=false` 表示轨迹不完整。",
        "应判为 `unassessed`（无法判断），并保留原始错误、原pass、原轨迹和后续复核/更正依据",
        "该条仍属于原manifest计划，不删除计划项，也不缩小分母N。",
        "本场景未执行设备/API，也没有读取题设对应的真实历史批次。"],
    3: [
        "合成8/8只说明既定合成样本下的回放结果，不能证明真机就绪，更不能替代真实5+2用例通过。",
        "还需核实设备二进制版本与单工具入口契约、工具/服务名称、真实参数及返回字段，评测前冻结预期错误判据，并确认初始状态、回读与恢复方法。",
        "`--mcp all` 可能运行已有的车窗、空调等配置测试，会有执行行为",
        "未支持或未执行项保留 `blocked` 原因及 `unassessed` 判定，继续计入原manifest分母N，不删除以抬高通过率。",
        "本场景未执行设备/API、采集或真实批次。"],
    4: [
        "在题设确认的16—30度规范要求拒绝越界参数、且40度请求与成功响应的真实关联证据完整时，N02应判 `fail`。",
        "保留设备/服务二进制与工具定义版本、冻结用例和错误判据、请求参数40、原始请求ID、完整原始响应及日志",
        "禁止看到结果后把预期从“拒绝”改成“成功”",
        "本地模板本身不能证明真实服务必须使用 `-32602`",
        "保留N02在原manifest计划分母N中，并计入失败F，不删除该条"]}


def grade():
    evidence = replay_checks()
    runs = []
    answers = {}
    ctx = load(WORK / "context/execution-context.json")
    for case_dir in sorted(WORK.glob("eval-*")):
        metadata = load(case_dir / "eval_metadata.json")
        eid = metadata["eval_id"]
        run_dir = case_dir / "with_skill"
        answer_path = run_dir / "outputs/answer.md"
        answer = answer_path.read_text()
        answer_hash = digest(answer_path)
        answers[str(answer_path.relative_to(WORK))] = answer_hash
        refs = citations(answer)
        checks = [True] * 5
        if eid == 1:
            checks[0] = all(load(WORK / f"logs/{name}.json")["exit_code"] == 0 for name in
                            ("check-env-help", "check-env", "cli-help", "run-help", "replay-dry-run", "replay-run"))
            checks[1] = all(evidence["checks"][name] for name in
                            ("output_path_inside_iteration", "uuid_requested_run_id", "four_files_exist", "run_ids_match", "all_artifacts_match"))
            checks[2] = all(evidence["checks"][name] for name in ("all_planned_items_preserved", "counts_match", "model_repeat_match"))
            checks[3] = all(evidence["checks"][name] for name in ("all_completed_synthetic", "recording_hash_matches", "source_ids_match"))
        if eid == 3:
            checks[1] = load(ROOT / "configs/servers/ark_mcp_service.json")["device_serial"] == "" \
                and "`tools_file`" in answer
        if eid == 4:
            n02 = load(ROOT / "tests/cases/l1/N02_param_out_of_range.json")
            checks[3] = n02["arguments"]["temperature"] == 40 and n02["assertions"][0]["type"] == "error_expected" \
                and "开发判据" in n02["expected_source"]
        checks[4] = checks[4] and refs["valid"]
        expectations = []
        for index, (text, quote) in enumerate(zip(metadata["assertions"], SEMANTIC_EVIDENCE[eid])):
            passed = checks[index] and quote in answer
            expectations.append({"text": text, "passed": passed,
                "evidence": f"outputs/answer.md：{quote}；内联语义复核。"
                + (" replay-artifact-checks.json核对真实产物。" if eid == 1 else "按题设和引用原文核对，不要求真实设备执行。")
                + (" 引用定义、路径与行范围校验通过。" if index == 4 and refs["valid"] else "")})
        passed = sum(exp["passed"] for exp in expectations)
        timing = dict(NULL_TIMING)
        save(str((run_dir / "timing.json").relative_to(WORK)), timing)
        grading = {
            "execution_mode": "main_context_fallback_nonindependent", "grader_mode": "inline_same_context",
            "answer_sha256": answer_hash, "expectations": expectations,
            "summary": {"passed": passed, "failed": 5 - passed, "total": 5, "pass_rate": passed / 5},
            "execution_metrics": {"tool_calls": None, "total_tool_calls": None, "total_steps": None,
                                  "errors_encountered": None, "output_chars": len(answer), "transcript_chars": None},
            "timing": {"executor_duration_seconds": None, "grader_duration_seconds": None, "total_duration_seconds": None},
            "claims": [{"claim": "引用编号、路径和行范围真实", "type": "factual", "verified": refs["valid"],
                        "evidence": "引用编号、路径、行范围和文件SHA-256详见本条citation_checks。", "citation_checks": refs},
                       {"claim": "本输出是独立with_skill代理运行", "type": "process", "verified": False,
                        "evidence": "答案主动声明非独立主上下文；此处登记未满足的请求条件，不表示答案作出了该宣称。"}],
            "user_notes_summary": {"uncertainties": ["没有独立子代理；已知全部场景/expectations；无隔离基线。"],
                                   "needs_review": ["独立行为对照、用户反馈、自动触发与导师验收均未完成。"],
                                   "workarounds": ["仅做当前Skill主上下文检查，禁止冒充without_skill。"]},
            "eval_feedback": {"suggestions": [{"reason": "这些场景明确给出错误线索，公共README也覆盖相同规则。必须由真正隔离的无Skill基线判断区分力；单组通过不证明增量。"}],
                              "overall": "5项内容断言可复核；独立性失败单独记录，不伪造失败基线或比较统计。"}}
        save(str((run_dir / "grading.json").relative_to(WORK)), grading)
        save(str((run_dir / "status.json").relative_to(WORK)), {
            "requested_independent_run": "blocked", "fallback_status": "completed",
            "context_id": "main-session-shared", "independent": False})
        baseline_dir = case_dir / "without_skill"
        save(str((baseline_dir / "status.json").relative_to(WORK)), {
            "status": "not_run", "reason": "No subagent/isolated-context tool exposed in this session",
            "is_old_skill": False, "input_policy": ctx["baseline_required_policy"],
            "actual_reads": [], "actual_writes_by_baseline": [], "actual_commands": [],
            "assertions": [{"text": a, "status": "not_run"} for a in metadata["assertions"]],
            "grading_emitted": False, "answer_emitted": False})
        save(str((baseline_dir / "timing.json").relative_to(WORK)), timing)
        runs.append({"eval_id": eid, "eval_name": metadata["eval_name"], "configuration": "with_skill",
                     "run_number": 1, "execution_mode": "main_context_fallback_nonindependent",
                     "result": dict(grading["summary"], time_seconds=None, tokens=None, tool_calls=None, errors=None),
                     "expectations": expectations, "notes": ["非独立主上下文检查；without_skill未运行。"]})
    save("context/answer-hashes.json", answers)
    # Only use the official numerical helper on observed content scores. Do not
    # call its loader: it substitutes output characters for missing tokens.
    official = runpy.run_path(str(CREATOR / "scripts/aggregate_benchmark.py"))
    stats = official["calculate_stats"]([r["result"]["pass_rate"] for r in runs])
    save("logs/aggregation.json", {"method": "official calculate_stats, called through runpy.run_path",
        "script": str(CREATOR / "scripts/aggregate_benchmark.py"),
        "sha256": digest(CREATOR / "scripts/aggregate_benchmark.py"),
        "input": [r["result"]["pass_rate"] for r in runs], "output": stats,
        "unknown_metric_policy": "No token character proxies; no zero-filled missing runs; no comparison delta."})
    notes = [
        "只有4个主上下文with_skill检查；独立上下文实际0/8。without_skill是未运行的无Skill基线，不是旧版。",
        "内容断言得分不证明Skill增量。主会话提前读取了场景、期望、Skill及公共资料，不能排除提示线索和自评偏差。",
        "without_skill缺少原始输出，没有分数；不能说两组同分、胜出或无增量。",
        "无子代理token/耗时返回，所有相关指标均null，不使用字符数或CLI回放时延估算。",
        "每场景仅1次主上下文检查。下方with_skill均值/离散度只描述4场景内容断言，不能用于稳定性或统计显著性推断。",
        "实际新建CLI回放8项计划/8项通过，全部synthetic；未重新执行160项回归和7反例。",
        "command -v claude退出码1，无输出：当前PATH未找到claude。未安装、登录或产生模型费用。",
        "行为内容检查不等于自动触发验证或导师验收；原始Read工具转录仅在会话，磁盘保留源快照和实际子进程返回。"]
    save("analysis.json", notes)
    benchmark = {"metadata": {
        "skill_name": "mcp-eval（主上下文降级检查；非独立对照）", "skill_path": str(ROOT / "skills/mcp-eval"),
        "executor_model": "openai/gpt-6-astra", "analyzer_model": "openai/gpt-6-astra",
        "timestamp": datetime.now(timezone.utc).isoformat(), "evals_run": [1, 2, 3, 4],
        "runs_per_configuration": None, "actual_runs_per_eval": {"with_skill": 1, "without_skill": 0},
        "requested_independent_runs": 8, "completed_independent_runs": 0, "fallback_sanity_runs": 4,
        "comparison_valid": False, "baseline_isolation_established": False},
        "runs": runs,
        "run_summary": {"with_skill": {"pass_rate": stats, "time_seconds": NULL_STATS, "tokens": NULL_STATS},
                        "without_skill": {"pass_rate": NULL_STATS, "time_seconds": NULL_STATS, "tokens": NULL_STATS},
                        "delta": {"pass_rate": None, "time_seconds": None, "tokens": None}},
        "not_run": [{"eval_id": i, "configuration": "without_skill", "reason": "no isolated context interface"} for i in range(1, 5)],
        "notes": notes}
    save("benchmark.json", benchmark)
    # The official viewer calls toFixed() on numeric means. A display-only
    # projection converts wholly unknown stats to null rather than inventing 0.
    view = json.loads(json.dumps(benchmark))
    for group in ("with_skill", "without_skill"):
        for metric in ("pass_rate", "time_seconds", "tokens"):
            if view["run_summary"][group][metric]["mean"] is None:
                view["run_summary"][group][metric] = None
    save("benchmark-viewer.json", view)
    lines = ["# 本轮内容断言结果（非独立对照）", "",
             "独立运行0/8；with_skill为主上下文检查。without_skill未运行，不计0分，也不参与均值或差值。", "",
             "| 场景 | with_skill内容断言 | without_skill |", "|---|---|---|"]
    for run in runs:
        result = run["result"]
        lines.append(f"| {run['eval_id']} {run['eval_name']} | {result['passed']}/{result['total']} | 未运行，5项均未评分 |")
    for run in runs:
        lines.extend(["", f"## 场景{run['eval_id']}", ""])
        for exp in run["expectations"]:
            lines.append(f"- {'PASS' if exp['passed'] else 'FAIL'} — {exp['text']}\n  - {exp['evidence']}")
    lines.extend(["", "## 限制", ""] + [f"- {n}" for n in notes])
    with (WORK / "benchmark.md").open("x") as stream:
        stream.write("\n".join(lines) + "\n")
    print(json.dumps({"fallback_content_scores": [{"eval_id": r["eval_id"], **r["result"]} for r in runs],
                      "independent_runs": 0, "baseline_runs": 0}, ensure_ascii=False, indent=2))


def review(log_name="review-generator"):
    command(log_name, [str(PYTHON), str(CREATOR / "eval-viewer/generate_review.py"), str(WORK),
            "--skill-name", "mcp-eval：主上下文检查，非独立对照", "--benchmark", str(WORK / "benchmark-viewer.json"),
            "--static", str(WORK / "review.html")])


def verify():
    benchmark = load(WORK / "benchmark.json")
    hashes = load(WORK / "context/answer-hashes.json")
    check = {"answers_unchanged": all(digest(WORK / p) == h for p, h in hashes.items()),
             "four_fallbacks_only": len(benchmark["runs"]) == 4 and len(benchmark["not_run"]) == 4,
             "unknown_tokens_times_null": all(r["result"]["tokens"] is None and r["result"]["time_seconds"] is None for r in benchmark["runs"]),
             "no_delta": all(v is None for v in benchmark["run_summary"]["delta"].values())}
    for case_dir in sorted(WORK.glob("eval-*")):
        eid = load(case_dir / "eval_metadata.json")["eval_id"]
        grading = load(case_dir / "with_skill/grading.json")
        check[f"eval_{eid}_grading_schema"] = len(grading["expectations"]) == 5 and all(
            isinstance(e["text"], str) and isinstance(e["passed"], bool) and isinstance(e["evidence"], str)
            for e in grading["expectations"]) and grading["summary"]["passed"] == sum(e["passed"] for e in grading["expectations"]) \
            and all(isinstance(c["evidence"], str) for c in grading["claims"])
        check[f"eval_{eid}_baseline_not_fabricated"] = not (case_dir / "without_skill/outputs").exists() \
            and not (case_dir / "without_skill/grading.json").exists() \
            and load(case_dir / "without_skill/status.json")["status"] == "not_run"
        check[f"eval_{eid}_output_files"] = sorted(p.name for p in (case_dir / "with_skill/outputs").iterdir()) == ["access-log.md", "answer.md"]
    html = (WORK / "review.html").read_text()
    match = re.search(r"const EMBEDDED_DATA = (.*?);\n", html)
    data = json.loads(match.group(1))
    check["viewer_four_original_outputs"] = len(data["runs"]) == 4 and all(
        any(f["name"] == "answer.md" and "非独立" in f["content"] for f in r["outputs"]) for r in data["runs"])
    check["viewer_has_no_history"] = not data["previous_outputs"] and not data["previous_feedback"]
    check["viewer_missing_stats_not_zero"] = data["benchmark"]["run_summary"]["without_skill"]["pass_rate"] is None
    boundary = load(WORK / "context/write-boundary-check.json")
    check["outside_files_unchanged"] = not any(boundary[k] for k in ("changed", "added", "removed"))
    check["all_replay_artifact_checks"] = all(load(WORK / "logs/replay-artifact-checks.json")["checks"].values())
    save("logs/final-verification.json", {"checks": check, "passed": all(check.values()),
        "scope": "JSON shape, actual replay, references, retained answers, write boundary and static embedded data; not browser runtime, independent evaluation or acceptance"})
    print(json.dumps(check, ensure_ascii=False, indent=2))
    assert all(check.values()), "See final-verification.json; do not silently discard failed checks"


if __name__ == "__main__":
    assert sys.dont_write_bytecode
    {"grade": grade, "review": review, "review-final": lambda: review("review-generator-final"), "verify": verify}[sys.argv[1]]()
