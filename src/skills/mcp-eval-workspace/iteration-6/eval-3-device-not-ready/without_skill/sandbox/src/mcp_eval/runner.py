"""运行编排：固定计划、独立批次、逐项收尾与可重建证据。"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import shlex
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .config import ConfigError, load_config, validate_tools
from .device import AdbRunner, DeviceChannel
from .judge import judge_record
from .model_loop import ModelLoop
from .providers import create_provider
from .records import EvalRecord, append_jsonl
from .replay import ReplayChannel
from .report import write_report


def local_path(root: Path, value: str | Path) -> Path:
    path = (root / value).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ConfigError(f"路径超出交付区: {value}")
    return path


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ConfigError(f"无法读取 JSON: {path}: {exc}") from exc


def _save_json(path: Path, data):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def load_tools(run: dict[str, Any], root: Path) -> list[dict[str, Any]]:
    if not run.get("tools_file"):
        return []
    path = local_path(root, run["tools_file"])
    data = _read_json(path)
    if isinstance(data, dict) and "tools_status" in data and data["tools_status"] != "complete":
        raise ConfigError("工具快照不完整；请处理采集错误或明确选择可用服务子集重新采集")
    if isinstance(data, dict) and "result" in data:
        data = data["result"]
    tools = data.get("tools") if isinstance(data, dict) else data
    return validate_tools(tools, str(path))


def load_cases(run: dict[str, Any], root: Path) -> list[dict[str, Any]]:
    local_path(root, run["case_glob"])
    if Path(run["case_glob"]).is_absolute():
        raise ConfigError("case_glob 必须为交付区内的相对模式")
    files = sorted(root.glob(run["case_glob"]))
    if not files:
        raise ConfigError(f"case_glob 未匹配到任何用例: {run['case_glob']}")
    cases = [load_config(local_path(root, path), "case") for path in files]
    ids = [case["case_id"] for case in cases]
    if len(ids) != len(set(ids)):
        raise ConfigError("用例 case_id 重复")
    return cases


def plan(run, cases, root=None, models=None):
    models = models or []
    items = []
    for repeat in range(run.get("repeat", 1)):
        for case in cases:
            model_ids = [model["model_config_id"] for model in models] if case["level"] == "L2" else [None]
            for model_id in model_ids:
                items.append({"item_id": f"item-{len(items) + 1:05d}", "case_id": case["case_id"],
                              "level": case["level"], "category": case["category"], "action": case["action"],
                              "channel": run["channel"], "model": model_id, "repeat_index": repeat})
    l2_count = sum(case["level"] == "L2" for case in cases)
    return {"run_id": run["run_id"], "channel": run["channel"], "l1_cases": len(cases) - l2_count,
            "l2_cases": l2_count, "models": len(models), "repeat": run.get("repeat", 1),
            "total_planned": len(items), "planned_items": items}


def build_channel(run: dict[str, Any], server: dict[str, Any], root: Path):
    if run["channel"] == "replay":
        return ReplayChannel(local_path(root, run["recording"]))
    return DeviceChannel(AdbRunner(serial=server["device_serial"]), service_bin=server.get("service_bin", "mcp_service"))


class ChannelExecutor:
    def __init__(self, channel, run_id="nested", case_id="adhoc"):
        self._channel, self.run_id, self.case_id = channel, run_id, case_id
        self.channel = channel.name
        self.source_type = getattr(channel, "source_type", "unknown")

    def __call__(self, name: str, arguments: dict, *, timeout: float) -> EvalRecord:
        case = {"case_id": self.case_id, "action": "tools_call", "service": "auto", "tool": name, "arguments": arguments}
        return self._channel.execute_case(case, self.run_id, timeout)


def _prepare(run_config_path, root):
    run = load_config(local_path(root, run_config_path), "run")
    server = load_config(local_path(root, run["server_ref"]), "server")
    cases = load_cases(run, root)
    models = [load_config(local_path(root, ref), "model") for ref in run.get("model_refs", [])]
    ids = [model["model_config_id"] for model in models]
    if len(ids) != len(set(ids)):
        raise ConfigError("model_config_id 重复")
    tools = load_tools(run, root)
    if any(case["level"] == "L2" for case in cases) and (not models or not tools):
        raise ConfigError("L2 必须配置 model_refs 与有效 tools_file")
    local_path(root, run["output_dir"])
    if run["channel"] == "replay":
        ReplayChannel(local_path(root, run["recording"]))  # 在执行前验证每条录制格式。
    elif not server["device_serial"].strip():
        raise ConfigError("device 模式必须填写 device_serial；尚未连接设备可用 replay 模式")
    warnings = []
    if run["channel"] == "device":
        warnings.append("未连接设备验证：须核实二进制版本、--toolscall 和日志完整响应输出")
        unsupported = [c["case_id"] for c in cases if c["level"] == "L1" and c["action"] != "tools_call"]
        if unsupported:
            warnings.append(f"当前单调用适配不支持发现/资源操作，这些条目将 blocked：{unsupported}")
    for model in models:
        if not os.environ.get(model["api_key_env"]):
            warnings.append(f"模型 {model['model_config_id']} 缺少环境变量 {model['api_key_env']}")
    return run, server, cases, models, tools, warnings


def _execute_item(item, case, run, channel, tools, models, *, checkpoint: Callable[[EvalRecord], None] | None = None):
    """同步执行单项；检查点在外部调用边界保存部分记录，回调异常向上传播。"""
    checkpoint = checkpoint or (lambda record: None)
    timeout = min(run.get("timeout_seconds", 30), case.get("timeout_seconds", run.get("timeout_seconds", 30)))
    if case["level"] == "L2":
        provider = create_provider(models[item["model"]])
        executor = ChannelExecutor(channel, run["run_id"], case["case_id"])
        return ModelLoop(provider, executor, tools, max_rounds=run.get("max_rounds", 5),
                         max_tool_calls=run.get("max_tool_calls", 10)).run_case(
                             case, run["run_id"], item["model"], timeout, checkpoint=checkpoint)
    start = time.monotonic()
    deadline = start + timeout
    pending = EvalRecord(run_id=run["run_id"], case_id=case["case_id"], channel=channel.name,
                         action=case["action"], service=case["service"], tool=case.get("tool"),
                         arguments=case.get("arguments"), source_type=getattr(channel, "source_type", "unknown"),
                         execution_status="error", error_category="execution_in_progress",
                         events=[{"kind": "primary_started", "tool": case.get("tool"), "arguments": case.get("arguments")}])
    checkpoint(pending)
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        pending.execution_status, pending.error_category = "timeout", "task_deadline_before_dispatch"
        pending.latency_ms = max(0, int((time.monotonic() - start) * 1000))
        checkpoint(pending)
        return pending
    record = channel.execute_case(case, run["run_id"], remaining)
    record.provenance["primary_latency_ms"] = record.latency_ms
    record.provenance["postconditions"] = []

    def deadline_exceeded():
        if time.monotonic() < deadline:
            return False
        record.execution_status, record.trace_complete = "timeout", False
        record.error_category = "task_deadline_exceeded"
        return True

    deadline_exceeded()
    checkpoint(record)
    if record.execution_status == "completed":
        for condition in case.get("postconditions", []):
            if deadline_exceeded():
                break
            followup = {**case, "action": "tools_call", "service": "auto",
                        "tool": condition["tool"], "arguments": condition["arguments"]}
            record.events.append({"kind": "postcondition_started", "tool": condition["tool"],
                                  "arguments": condition["arguments"]})
            checkpoint(record)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                deadline_exceeded()
                break
            result = channel.execute_case(followup, run["run_id"], remaining)
            record.provenance["postconditions"].append(result.to_dict())
            expired = deadline_exceeded()
            checkpoint(record)
            if expired:
                break
    if channel.name == "device":
        record.latency_ms = max(0, int((time.monotonic() - start) * 1000))
    else:
        record.provenance["replay_wall_ms"] = max(0, int((time.monotonic() - start) * 1000))
    checkpoint(record)
    return record


def _mark_incomplete(record: EvalRecord, case: dict, category: str, detail: str) -> EvalRecord:
    """保留已有证据；已观察到的禁止调用仍由判定器记为失败。"""
    record.execution_status, record.trace_complete = "error", False
    record.error_category = category
    record.events.append({"kind": category, "detail": detail, "remote_state": "not_confirmed"})
    judge_record(case, record)
    if record.verdict == "unassessed":
        record.verdict_reason = detail + "；保留已有执行证据，远端状态需核对"
    return record


def run_evaluation(run_config_path: str | Path, root: str | Path, *, dry_run: bool = False) -> dict[str, Any]:
    root = Path(root).resolve()
    run, server, cases, models, tools, warnings = _prepare(run_config_path, root)
    info = plan(run, cases, models=models)
    if dry_run:
        return {"plan": info, "executed": 0, "warnings": warnings, "device_verified": False}
    channel = build_channel(run, server, root)
    requested_id = run["run_id"]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run = {**run, "run_id": f"{requested_id}-{stamp}-{uuid.uuid4().hex[:8]}"}
    out = local_path(root, run["output_dir"]) / run["run_id"]
    out.mkdir(parents=True, exist_ok=False)
    (out / "artifacts").mkdir()
    manifest = {"schema_version": 2, "run_id": run["run_id"], "requested_run_id": requested_id,
                "state": "running", "planned_items": info["planned_items"], "warnings": warnings,
                "inputs": {"run": run, "server": server, "cases": cases, "models": models, "tools": tools},
                "python": platform.python_version(), "engine_sources": {
                    str(path.relative_to(Path(__file__).parent)): hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in sorted(Path(__file__).parent.rglob("*.py"))}}
    if run.get("recording"):
        contents = local_path(root, run["recording"]).read_bytes()
        (out / "recording-input.jsonl").write_bytes(contents)
        manifest["recording_sha256"] = hashlib.sha256(contents).hexdigest()
    if run.get("tools_file"):
        contents = local_path(root, run["tools_file"]).read_bytes()
        (out / "tools-input.json").write_bytes(contents)
        manifest["tools_input_sha256"] = hashlib.sha256(contents).hexdigest()
    _save_json(out / "manifest.json", manifest)
    results_path = out / "results.jsonl"
    results_path.touch(exist_ok=False)
    by_case, by_model = {c["case_id"]: c for c in cases}, {m["model_config_id"]: m for m in models}
    interrupted, count = False, 0
    stored_ids = set()
    try:
        for item in info["planned_items"]:
            case = by_case[item["case_id"]]
            partial = None

            def checkpoint(record):
                nonlocal partial
                if (record.case_id, record.model, record.channel) != (case["case_id"], item["model"], run["channel"]):
                    raise ValueError("执行器结果身份与计划不符")
                record.item_id, record.repeat_index = item["item_id"], item["repeat_index"]
                record.evidence = [f"artifacts/{item['item_id']}.json"]
                partial = EvalRecord.from_dict(record.to_dict())
                _save_json(out / record.evidence[0], partial.to_dict())

            def failed_record(category, detail):
                record = partial or EvalRecord(run_id=run["run_id"], case_id=case["case_id"], channel=run["channel"],
                                               action=case["action"], service=case["service"], model=item["model"],
                                               tool=case.get("tool"), arguments=case.get("arguments"))
                return _mark_incomplete(record, case, category, detail)

            count += 1  # 对外executed为尝试项数，不代表工具已成功执行。
            try:
                record = _execute_item(item, case, run, channel, tools, by_model, checkpoint=checkpoint)
                if (record.case_id, record.model, record.channel) != (case["case_id"], item["model"], run["channel"]):
                    raise ValueError("执行器结果身份与计划不符")
                judge_record(case, record)
            except KeyboardInterrupt:
                interrupted = True
                record = failed_record("interrupted", "当前条目执行中断")
            except (OSError, ValueError, RuntimeError, TypeError, KeyError) as exc:
                record = failed_record("evaluation_error", f"执行或判定异常: {type(exc).__name__}: {exc}")
            checkpoint(record)
            append_jsonl(results_path, record)
            stored_ids.add(item["item_id"])
            if interrupted:
                break
    except KeyboardInterrupt:
        interrupted = True
    finally:
        final_records = []
        for item in info["planned_items"]:
            case = by_case[item["case_id"]]
            artifact = out / "artifacts" / f"{item['item_id']}.json"
            if artifact.is_file():
                missing = EvalRecord.from_dict(_read_json(artifact))
                if item["item_id"] not in stored_ids and missing.verdict is None:
                    _mark_incomplete(missing, case, "interrupted", "批次中断，从检查点恢复部分记录")
                    _save_json(artifact, missing.to_dict())
            else:
                missing = EvalRecord(run_id=run["run_id"], case_id=item["case_id"], item_id=item["item_id"],
                                     repeat_index=item["repeat_index"], model=item["model"], channel=run["channel"],
                                     action=case["action"], service=case["service"], execution_status="not_run",
                                     error_category="interrupted", verdict="unassessed", verdict_reason="批次中断，条目未执行")
            final_records.append(missing.to_dict())
        # artifact为原子检查点；收尾时重建JSONL，避免追加中断产生半行或重复条目。
        temporary = results_path.with_suffix(".jsonl.tmp")
        temporary.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in final_records), encoding="utf-8")
        temporary.replace(results_path)
        manifest["state"] = "interrupted" if interrupted else "finished"
        manifest["recorded_items"], manifest["attempted_items"] = len(info["planned_items"]), count
        _save_json(out / "manifest.json", manifest)
        summary, report = write_report(results_path, by_case, out, run["run_id"], info["planned_items"])
    summary_data = _read_json(summary)
    counts = {verdict: sum(group[verdict] for group in summary_data["groups"].values())
              for verdict in ("pass", "fail", "unassessed")}
    return {"plan": info, "run_id": run["run_id"], "executed": count, "interrupted": interrupted, "counts": counts,
            "results": str(results_path), "summary": str(summary), "report": str(report),
            "manifest": str(out / "manifest.json"), "warnings": warnings}


def on_device_checklist(server: dict[str, Any]) -> str:
    """生成预检指引；设备事实未验证时不宣称清单可直接全量执行。"""
    serial = server.get("device_serial", "")
    if not serial:
        return ("# 上机预检（尚未就绪）\n\n先在 Ubuntu Bash 执行 adb devices，确认目标设备状态为 device，"
                "将第一列序列号填入 server 配置的 device_serial 后重新生成。不要直接执行含占位符的命令。\n")
    adb = shlex.join(["adb", "-s", serial])
    binary = shlex.quote(server.get("service_bin", "mcp_service"))
    return f"""# 上机预检（设备契约待现场核实）

所有命令在开发机 Ubuntu Bash、交付区根目录执行；adb shell 内的命令才在车机运行。

1. 核对连接：`adb devices`，目标序列号必须为 `{serial}` 且状态为 device。
2. 只读查看二进制用法：`{adb} shell {binary}`。该源码无参数打印用法并返回非零，需人工核对是否包含 --toolscall。
3. 只读记录本地基线：`git -C {shlex.quote(server['baseline_tree'])} rev-parse HEAD`。这不是设备二进制版本证明。
4. 完整工具目录必须来自可追溯的 JSON 导出。当前 --mcp all 会执行已有测试，不能用作只读发现。
5. 冻结已核对的工具名、参数、预期及恢复方法后，先运行单条调用，再扩大批次。
6. 配置预检：`PYTHONPATH=src python3 -m mcp_eval run configs/runs/l1_device.json --dry-run`。预检不连接车机。
7. 正式运行：`PYTHONPATH=src python3 -m mcp_eval run configs/runs/l1_device.json`。仅 --toolscall 已实现，其他动作保留 blocked。
8. L2 需完整 tools_file 和模型密钥；先验证模型配置，再使用 l2_device.json。
9. 每次运行返回独立输出目录，保存 manifest、results、artifacts 与报告；按确认的业务方法恢复原状态并记录。

root、重启与状态修改按设备实际需要执行，不在预检中自动触发。未验证的响应/发现接口应明确记录为阻塞。
"""
