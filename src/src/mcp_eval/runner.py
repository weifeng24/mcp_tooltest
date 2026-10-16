"""运行编排：加载运行配置 → 建通道 → 执行 → 判定 → 出报告。

所有相对路径（server_ref / case_glob / recording / tools_file / output_dir）
均相对交付区根目录解析。dry_run 只校验与展示计划，不执行。
"""
from __future__ import annotations

import glob
from pathlib import Path
from typing import Any

from .config import ConfigError, load_config
from .device import AdbRunner, DeviceChannel
from .judge import judge_record
from .model_loop import ModelLoop
from .providers import create_provider
from .records import EvalRecord, append_jsonl
from .replay import ReplayChannel
from .report import write_report


class ChannelExecutor:
    """把 device/replay 通道适配为 ModelLoop 的工具执行器。"""

    def __init__(self, channel: Any) -> None:
        self._channel = channel
        self.channel = channel.name

    def __call__(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        case = {
            "case_id": "adhoc",
            "action": "tools_call",
            "service": "auto",
            "tool": name,
            "arguments": arguments,
        }
        record = self._channel.execute_case(case, "adhoc")
        if record.execution_status != "completed" or record.response_raw is None:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"工具执行失败: {record.error_category or record.execution_status}",
                    }
                ],
                "isError": True,
            }
        return record.response_raw


def build_channel(run: dict[str, Any], server: dict[str, Any], root: Path) -> Any:
    if run["channel"] == "replay":
        return ReplayChannel(root / run["recording"])
    runner = AdbRunner(serial=server.get("device_serial", ""))
    return DeviceChannel(runner=runner)


def load_cases(run: dict[str, Any], root: Path) -> list[dict[str, Any]]:
    files = sorted(glob.glob(str(root / run["case_glob"])))
    if not files:
        raise ConfigError(f"case_glob 未匹配到任何用例: {run['case_glob']}")
    return [load_config(f, "case") for f in files]


def load_tools(run: dict[str, Any], root: Path) -> list[dict[str, Any]]:
    if not run.get("tools_file"):
        return []
    import json

    data = json.loads((root / run["tools_file"]).read_text(encoding="utf-8"))
    tools = data.get("tools", data) if isinstance(data, dict) else data
    if not isinstance(tools, list):
        raise ConfigError(f"tools_file 格式错误（期望工具数组）: {run['tools_file']}")
    return tools


def plan(run: dict[str, Any], cases: list[dict[str, Any]], root: Path) -> dict[str, Any]:
    """计算运行计划（不执行）：用例 × 模型 × 重复次数。"""
    l2_cases = [c for c in cases if c["level"] == "L2"]
    models = run.get("model_refs") or []
    return {
        "run_id": run["run_id"],
        "channel": run["channel"],
        "l1_cases": len(cases) - len(l2_cases),
        "l2_cases": len(l2_cases),
        "models": len(models) if l2_cases else 0,
        "repeat": run.get("repeat", 1),
        "total_planned": ((len(cases) - len(l2_cases)) + len(l2_cases) * max(len(models), 1))
        * run.get("repeat", 1),
    }


def run_evaluation(
    run_config_path: str | Path, root: str | Path, *, dry_run: bool = False
) -> dict[str, Any]:
    root = Path(root)
    run = load_config(root / run_config_path, "run")
    server = load_config(root / run["server_ref"], "server")
    cases = load_cases(run, root)
    info = plan(run, cases, root)
    if dry_run:
        return {"plan": info, "executed": 0}

    channel = build_channel(run, server, root)
    tools = load_tools(run, root)
    models = [load_config(root / ref, "model") for ref in (run.get("model_refs") or [])]
    l2_cases = [c for c in cases if c["level"] == "L2"]
    if l2_cases:
        if not models:
            raise ConfigError("存在 L2 用例但 run 未配置 model_refs")
        if not tools:
            raise ConfigError("存在 L2 用例但 run 未配置 tools_file（tools/list 采集文件）")

    out_dir = root / run["output_dir"] / run["run_id"]
    out_dir.mkdir(parents=True, exist_ok=True)
    results_path = out_dir / "results.jsonl"
    if results_path.exists():
        results_path.unlink()  # 同一 run_id 重跑时覆盖旧结果，避免混计

    timeout = run.get("timeout_seconds", 30)
    executed = 0
    for _repeat in range(run.get("repeat", 1)):
        for case in cases:
            if case["level"] == "L2":
                continue
            record = channel.execute_case(case, run["run_id"], timeout)
            judge_record(case, record)
            append_jsonl(results_path, record)
            executed += 1
        for case in l2_cases:
            for model_cfg in models:
                provider = create_provider(model_cfg)
                executor = ChannelExecutor(channel)
                loop = ModelLoop(provider, executor, tools)
                record = loop.run_case(
                    case, run["run_id"], model_cfg["model_config_id"], timeout
                )
                judge_record(case, record)
                append_jsonl(results_path, record)
                executed += 1

    cases_by_id = {c["case_id"]: c for c in cases}
    summary_path, report_path = write_report(results_path, cases_by_id, out_dir, run["run_id"])
    return {
        "plan": info,
        "executed": executed,
        "results": str(results_path),
        "summary": str(summary_path),
        "report": str(report_path),
    }


def on_device_checklist(server: dict[str, Any]) -> str:
    """生成上机日检查清单（命令按 server 配置填充）。"""
    serial = server.get("device_serial") or "<device_serial>"
    adb = f"adb -s {serial}"
    return f"""# 上机日检查清单（server: {server['server_id']}）

## 1. 环境确认
{adb} devices
{adb} root
cd {server['baseline_tree']} && git rev-parse HEAD   # 期望 {server['baseline_commit']}

## 2. 协议与工具采集（留档到 tests/results/<run-id>/）
{adb} shell "mcp_service -c -t --svcmap"
{adb} shell "mcp_service -c -t --list"
{adb} shell "mcp_service -c -t --mcp all"     # tools/list 全量；输出存为 tools 采集文件

## 3. L1 正式批次
PYTHONPATH=src python3 -m mcp_eval run configs/runs/l1_device.json

## 4. L2 双模型批次（如需；先 export DEEPSEEK_API_KEY / KIMI_API_KEY）
PYTHONPATH=src python3 -m mcp_eval run configs/runs/l2_device.json

## 5. 状态恢复
{adb} shell "mcp_service -c -t --camera --stop"   # 如有相机用例
# 确认空调等被修改状态恢复原值；必要时重启 mcp_service

## 6. 证据回采
{adb} logcat -d > tests/results/<run-id>/logcat.txt
{adb} pull /data/local/tmp/mcp_eval tests/results/<run-id>/device_artifacts
"""
