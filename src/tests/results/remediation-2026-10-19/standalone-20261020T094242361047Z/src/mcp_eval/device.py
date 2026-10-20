"""经 adb 调用已核对的 --toolscall 入口；不覆盖车端系统配置。

当前车端 CLI 的单次 ToolsCall 请求 id 固定为 1。每次 adb 进程独立采集，
只接受该 id 的完整响应。工具发现/资源读取需另有经过验证的采集入口，
不使用会执行既有状态修改的 --mcp all 来代替只读发现。
"""
from __future__ import annotations

import json
import shlex
import subprocess
import time
from dataclasses import dataclass
from typing import Any, Callable

from .records import EvalRecord


@dataclass
class AdbResult:
    returncode: int
    stdout: str
    stderr: str
    latency_ms: int
    timed_out: bool = False


def _text(value):
    return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value or ""


class AdbRunner:
    def __init__(self, adb_bin: str = "adb", serial: str = ""):
        self.adb_bin, self.serial = adb_bin, serial

    def __call__(self, args: list[str], timeout: float) -> AdbResult:
        if not self.serial:
            return AdbResult(2, "", "未指定 device_serial", 0)
        command = [self.adb_bin, "-s", self.serial, *args]
        start = time.monotonic()
        try:
            proc = subprocess.run(command, capture_output=True, text=True, encoding="utf-8",
                                  errors="replace", timeout=max(timeout, 0.001))
            return AdbResult(proc.returncode, proc.stdout, proc.stderr, int((time.monotonic() - start) * 1000))
        except subprocess.TimeoutExpired as exc:
            return AdbResult(-1, _text(exc.stdout), _text(exc.stderr),
                             int((time.monotonic() - start) * 1000), True)
        except OSError as exc:
            return AdbResult(127, "", str(exc), int((time.monotonic() - start) * 1000))


def extract_jsonrpc(text: str) -> list[dict[str, Any]]:
    """从日志中解码完整 JSON 对象；只保留响应，不接受请求回显。"""
    decoder, found, position = json.JSONDecoder(), [], 0
    while position < len(text):
        start = text.find("{", position)
        if start < 0:
            break
        try:
            obj, end = decoder.raw_decode(text, start)
            position = end
        except json.JSONDecodeError:
            position = start + 1
            continue
        if not isinstance(obj, dict) or obj.get("jsonrpc") != "2.0" or "id" not in obj or "method" in obj:
            continue
        if ("result" in obj) == ("error" in obj):
            continue
        if "result" in obj and not isinstance(obj["result"], dict):
            continue
        if "error" in obj:
            error = obj["error"]
            if not isinstance(error, dict) or type(error.get("code")) is not int or not isinstance(error.get("message"), str):
                continue
        found.append(obj)
    return found


def command_for_case(case: dict[str, Any], service_bin: str = "mcp_service") -> list[str]:
    if case["action"] != "tools_call":
        raise ValueError(f"当前车端适配不支持 {case['action']}")
    tool, arguments = case.get("tool"), case.get("arguments", {})
    if not isinstance(tool, str) or not tool or not isinstance(arguments, dict):
        raise ValueError("tools_call 需要完整工具名及对象参数")
    command = [service_bin, "-c", "-t", "--toolscall", tool]
    # 车端 TestToolsCall 的空 JSON 参数会触发 arg0 回退；无参工具不传 ARGS。
    if arguments:
        command.append(json.dumps(arguments, ensure_ascii=False, separators=(",", ":")))
    return command


def build_test_config(case: dict[str, Any]) -> dict[str, Any]:
    """历史配置格式参考；DeviceChannel 不消费此文件，不可直接用于上机。"""
    interface: dict[str, Any] = {"service_name": case["service"]}
    action = case["action"]
    if action == "tools_list":
        interface.update(test_tools_list=True, test_resources_list=True)
    elif action == "tools_call":
        interface["test_tools_call"] = {"name": case["tool"], "arguments": case.get("arguments", {})}
    elif action in ("resources_list", "resources_read"):
        interface["test_resources_list"] = True
        if action == "resources_read":
            interface["test_resources_read"] = [case.get("resource_uri", case.get("tool"))]
    else:
        raise ValueError(f"build_test_config 不支持 action={action}")
    return {"client_tests": {"mcp_interface": interface}}


class DeviceChannel:
    name = "device"
    source_type = "live_device"

    def __init__(self, runner: Callable[[list[str], float], AdbResult], *, service_bin: str = "mcp_service"):
        self.runner, self.service_bin = runner, service_bin

    def execute_case(self, case: dict[str, Any], run_id: str, timeout: float = 30) -> EvalRecord:
        base = dict(run_id=run_id, case_id=case["case_id"], channel=self.name, action=case["action"],
                    service=case["service"], tool=case.get("tool"), arguments=case.get("arguments"),
                    source_type=self.source_type)
        if case["action"] != "tools_call":
            return EvalRecord(**base, execution_status="blocked", error_category="unsupported_action")
        command = command_for_case(case, self.service_bin)
        request = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                   "params": {"name": case["tool"], "arguments": case.get("arguments", {})}}
        result = self.runner(["shell", shlex.join(command)], min(timeout, case.get("timeout_seconds", timeout)))
        record = self.record_from_result(base, result, request)
        record.events.append({"kind": "device_command", "argv": command, "request": request,
                              "returncode": result.returncode})
        return record

    def record_from_result(self, base: dict[str, Any], result: AdbResult, request_raw: dict[str, Any]) -> EvalRecord:
        record = EvalRecord(**base, request_raw=request_raw, latency_ms=result.latency_ms,
                            stdout=result.stdout, stderr=result.stderr, stdout_tail=result.stdout[-2000:])
        frames = extract_jsonrpc(result.stdout + "\n" + result.stderr)
        expected_id = request_raw.get("id", 1)
        matching = {json.dumps(frame, sort_keys=True, ensure_ascii=False): frame for frame in frames
                    if frame["id"] == expected_id and type(frame["id"]) is type(expected_id)}
        record.events.append({"kind": "response_candidates", "frames": frames})
        if len(matching) == 1:
            record.response_raw = next(iter(matching.values()))
        if result.timed_out:
            record.execution_status, record.error_category = "timeout", "adb_timeout_remote_state_unknown"
        elif result.returncode:
            record.execution_status, record.error_category = "error", "exit_nonzero"
        elif not matching:
            record.execution_status, record.error_category = "error", "response_missing"
        elif len(matching) != 1:
            record.execution_status, record.error_category = "error", "response_ambiguous"
        else:
            record.execution_status, record.trace_complete = "completed", True
        return record
