"""只读审查的离线反例；仅在本目录创建隔离测试产物，不调用 adb 或网络。

从交付区运行：python3 -B tests/results/review-2026-10-16/reproduce.py
反例中的 observed 是当前行为，expected 是设计所要求的行为。
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
sys.path.insert(0, str(ROOT / "src"))

from mcp_eval.config import load_config, validate_config
from mcp_eval.device import AdbResult, DeviceChannel, extract_jsonrpc
from mcp_eval.judge import judge_record
from mcp_eval.model_loop import ModelLoop
from mcp_eval.providers.base import ProviderError, ProviderResponse, ToolCallDecision
from mcp_eval.records import EvalRecord, append_jsonl, read_jsonl
from mcp_eval.replay import ReplayChannel
from mcp_eval.report import render_markdown, summarize
from mcp_eval.runner import load_tools, run_evaluation


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def case(name):
    path = next((ROOT / "tests/cases").rglob(name + "_*.json"))
    return load_config(path, "case")


def record(c, **fields):
    data = dict(run_id="review", case_id=c["case_id"], channel="replay",
                action=c["action"], service=c["service"], tool=c.get("tool"),
                arguments=c.get("arguments"), execution_status="completed")
    return EvalRecord(**{**data, **fields})


class ScriptedProvider:
    def __init__(self, *responses):
        self.responses = iter(responses)

    def chat(self, messages, tools):
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response


class OfflineExecutor:
    channel = "replay"

    def __init__(self):
        self.calls = []

    def __call__(self, name, arguments):
        self.calls.append((name, arguments))
        return {"isError": False, "content": [{"type": "text", "text": "synthetic"}]}


TOOLS = [{"name": "HvacService.setTemp", "inputSchema": {
    "type": "object", "properties": {"temperature": {
        "type": "integer", "minimum": 16, "maximum": 30}}, "required": ["temperature"]}}]


def main():
    observations = []

    def observe(id_, expected, observed, bug):
        observations.append(dict(id=id_, expected=expected, observed=observed,
                                 reproduced=bool(bug)))

    # 原测试套件在隔离副本执行，避免 test_runner 覆盖已存在的回放记录。
    with tempfile.TemporaryDirectory(prefix="baseline-", dir=OUT) as temp:
        sandbox = Path(temp)
        ignore = shutil.ignore_patterns("__pycache__", ".pytest_cache", "*.pyc")
        for folder in ("src", "configs", "recordings"):
            shutil.copytree(ROOT / folder, sandbox / folder, ignore=ignore)
        shutil.copytree(ROOT / "tests/cases", sandbox / "tests/cases")
        shutil.copy2(ROOT / "pytest.ini", sandbox / "pytest.ini")
        proc = subprocess.run(
            [sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider",
             "--basetemp", str(sandbox / "pytest-temp"),
             "--junitxml", str(OUT / "baseline-pytest.xml")],
            cwd=sandbox, capture_output=True, text=True, timeout=120)
        (OUT / "baseline-pytest.txt").write_text(proc.stdout + proc.stderr, encoding="utf-8")
        baseline = {"returncode": proc.returncode, "isolated": True}

    with tempfile.TemporaryDirectory(prefix="probes-", dir=OUT) as temp:
        sandbox = Path(temp)
        p02, m01, m03 = case("P02"), case("M01"), case("M03")
        calls = []

        def fake_adb(args, timeout):
            calls.append(args)
            text = "" if len(calls) == 1 else '{"jsonrpc":"2.0","id":1,"result":{"success":true}}'
            return AdbResult(0, text, "", 1)

        DeviceChannel(fake_adb).execute_case(p02, "review")
        observe("R01-config-not-consumed", "车端执行指定用例配置并解析服务归属", calls,
                "--mcp auto" in calls[-1][-1] and "case_config.json" not in calls[-1][-1])

        output = ('{"jsonrpc":"2.0","id":1,"error":{"code":-32602}}\n'
                  '{"jsonrpc":"2.0","id":1001,"result":{"success":true}}')
        base = dict(run_id="review", case_id="N01", channel="device", action="tools_call",
                    service="MCPVehicleService")
        mapped = DeviceChannel(fake_adb).record_from_result(base, AdbResult(0, output, "", 1), {})
        observe("R02-unrelated-response", "选择该请求 id=1 的响应", mapped.response_raw,
                mapped.response_raw["id"] == 1001)
        multiline = json.dumps({"jsonrpc": "2.0", "id": 1, "result": {"tools": []}}, indent=2)
        observe("R02-multiline", "完整识别多行 JSON-RPC", extract_jsonrpc(multiline),
                not extract_jsonrpc(multiline))
        request_only = '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{}}'
        mapped = DeviceChannel(fake_adb).record_from_result(base, AdbResult(0, request_only, "", 1), {})
        observe("R02-request-as-response", "只有请求回显时判为未取得响应", mapped.execution_status,
                mapped.execution_status == "completed")

        executor = OfflineExecutor()
        provider = ScriptedProvider(ProviderResponse(tool_calls=[ToolCallDecision(
            "a", "HvacService_setTemp", {"temperature": 40})]), ProviderResponse(content="已设置"))
        result = ModelLoop(provider, executor, TOOLS).run_case(m01, "review", "offline")
        judge_record(m01, result)
        observe("R03-rejected-call-pass", "参数错误且未下发，M01 不应通过",
                {"verdict": result.verdict, "validation_errors": result.response_raw["validation_errors"],
                 "executed_calls": executor.calls}, result.verdict == "pass" and not executor.calls)

        provider = ScriptedProvider(ProviderResponse(tool_calls=[ToolCallDecision(
            "b", "HvacService_setTemp", {"temperature": 22})]))
        result = ModelLoop(provider, OfflineExecutor(), TOOLS, max_rounds=1).run_case(m01, "r", "offline")
        judge_record(m01, result)
        observe("R03-no-final-pass", "达到硬上限且无最终回答，不应通过",
                {"verdict": result.verdict, "stopped_reason": result.response_raw["stopped_reason"],
                 "final_answer": result.response_raw["final_answer"]}, result.verdict == "pass")

        result = ModelLoop(ScriptedProvider(ProviderError("synthetic provider outage")),
                           OfflineExecutor(), TOOLS).run_case(m03, "r", "offline")
        judge_record(m03, result)
        observe("R04-provider-error-pass", "模型请求失败应无法判断，不是正确不调用",
                {"execution_status": result.execution_status, "verdict": result.verdict},
                result.verdict == "pass")
        result = judge_record(m03, record(m03, response_raw=None))
        observe("R04-missing-evidence-pass", "没有完整调用记录应无法判断", result.verdict,
                result.verdict == "pass")

        now = [0.0]

        class SlowProvider:
            def chat(self, messages, tools):
                now[0] = 999.0
                return ProviderResponse(tool_calls=[ToolCallDecision(
                    "slow", "HvacService_setTemp", {"temperature": 22})])

        executor = OfflineExecutor()
        result = ModelLoop(SlowProvider(), executor, TOOLS, max_rounds=1,
                           clock=lambda: now[0]).run_case(m01, "r", "offline", timeout_seconds=1)
        observe("R05-after-deadline-call", "超时后不再调用执行器，记录 timeout",
                {"time": now[0], "execution_status": result.execution_status, "calls": executor.calls},
                bool(executor.calls) and result.execution_status == "completed")

        malformed = {**m01, "assertions": [{"type": "model_selects_tool"}]}
        validate_config(malformed, "case")
        result = judge_record(malformed, record(m01, response_raw={"tool_calls": [{"name": "wrong_tool"}]}))
        observe("R10-empty-assertion", "缺少工具选择判据时加载报错", result.verdict,
                result.verdict == "pass")

        response_path = sandbox / "tools.json"
        save(response_path, {"jsonrpc": "2.0", "id": 1, "result": {"tools": TOOLS}})
        try:
            load_tools({"tools_file": "tools.json"}, sandbox)
            error = None
        except Exception as exc:
            error = str(exc)
        observe("R08-tools-list-envelope", "能够读取约定 tools/list 原始响应", error, error is not None)

        source = sandbox / "source.jsonl"
        append_jsonl(source, record(p02, response_raw={"result": {"success": False}}))
        append_jsonl(source, record(p02, response_raw={"result": {"success": True}}))
        other = {**p02, "case_id": "P09"}
        replayed = ReplayChannel(source).execute_case(other, "new")
        observe("R07-replay-case-id", "回放输出关联当前用例 P09", replayed.case_id, replayed.case_id != "P09")
        channel = ReplayChannel(source)
        outcomes = [channel.execute_case(p02, "r").response_raw for _ in range(2)]
        observe("R07-replay-loses-sequence", "保留失败、成功两次录制，或拒绝歧义", outcomes,
                all(value["result"]["success"] for value in outcomes))

        cases = {"P01": {"level": "L1", "category": "positive"},
                 "P02": {"level": "L1", "category": "positive"}}
        single = record(case("P01"), verdict="pass")
        summary = summarize([single], cases)
        group = next(iter(summary["groups"].values()))
        observe("R06-denominator-shrinks", "固定计划 2 项，缺失项进入 unassessed", group,
                group["planned"] == 1 and group["judge_coverage"] == 1)
        md = render_markdown(summary, [single], "r")
        row = next(line for line in md.splitlines() if line.startswith("| replay|"))
        observe("R11-markdown-columns", "表头与数据均为 7 列", {"row": row, "cells": len(row.split("|")) - 2},
                len(row.split("|")) - 2 != 7)

        # 仅在临时根目录测试中断及覆盖；不会运行真实设备/模型。
        batch = sandbox / "batch"
        save(batch / "server.json", load_config(ROOT / "configs/servers/ark_mcp_service.json", "server"))
        save(batch / "cases/P01.json", case("P01"))
        save(batch / "cases/P02.json", p02)
        run = dict(run_id="review", channel="device", server_ref="server.json",
                   case_glob="cases/*.json", output_dir="out", repeat=1)
        save(batch / "run.json", run)
        result_path = batch / "out/review/results.jsonl"
        result_path.parent.mkdir(parents=True)
        result_path.write_text("prior evidence marker\n", encoding="utf-8")

        class InterruptedChannel:
            def execute_case(self, current, run_id, timeout):
                if current["case_id"] == "P02":
                    raise OSError("synthetic interruption")
                return record(current, response_raw={"result": {"tools": [
                    {"name": "svc.tool", "inputSchema": {"type": "object"}}]}})

        with patch("mcp_eval.runner.build_channel", return_value=InterruptedChannel()):
            try:
                run_evaluation("run.json", batch)
            except OSError:
                pass
        actual = dict(old_evidence_preserved="prior evidence marker" in result_path.read_text(),
                      saved_records=len(read_jsonl(result_path)),
                      report_exists=(batch / "out/review/report.md").exists())
        observe("R06-interrupted-run", "保留旧批次及未完成项并生成部分报告", actual,
                not actual["old_evidence_preserved"] and actual["saved_records"] == 1 and not actual["report_exists"])
        run["model_refs"] = ["missing-model.json"]
        save(batch / "run.json", run)
        dry = run_evaluation("run.json", batch, dry_run=True)
        observe("R08-dry-run-incomplete", "dry-run 应校验引用的模型配置存在", dry,
                dry["executed"] == 0)

    save(OUT / "probe-results.json", {"baseline": baseline, "observations": observations})
    print(f"Baseline pytest exit: {baseline['returncode']}")
    for item in observations:
        print(f"{item['id']}: {'REPRODUCED' if item['reproduced'] else 'NOT REPRODUCED'}")
    print(f"Total: {sum(item['reproduced'] for item in observations)}/{len(observations)}")
    return int(baseline["returncode"] != 0 or not all(item["reproduced"] for item in observations))


if __name__ == "__main__":
    raise SystemExit(main())
