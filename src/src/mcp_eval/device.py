"""adb 设备通道：在车机上执行用例并采集输出。

IO 与解析分离：AdbRunner 封装 subprocess 调用（真机才用到）；
DeviceChannel 接受可替换的 runner，解析与状态映射为纯函数，离线可测。

注意：自带测试客户端的输出格式待首次上机校准，解析策略以
extract_jsonrpc 的容错提取为起点，校准后收紧。
"""
from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .records import EvalRecord


@dataclass
class AdbResult:
    returncode: int
    stdout: str
    stderr: str
    latency_ms: int
    timed_out: bool = False


class AdbRunner:
    """真实的 adb 调用封装。无设备环境下不实例化使用。"""

    def __init__(self, adb_bin: str = "adb", serial: str = "") -> None:
        self.adb_bin = adb_bin
        self.serial = serial

    def __call__(self, args: list[str], timeout: int) -> AdbResult:
        cmd = [self.adb_bin]
        if self.serial:
            cmd += ["-s", self.serial]
        cmd += args
        start = time.monotonic()
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout
            )
            return AdbResult(
                returncode=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
                latency_ms=int((time.monotonic() - start) * 1000),
            )
        except subprocess.TimeoutExpired as exc:
            return AdbResult(
                returncode=-1,
                stdout=(exc.stdout or "") if isinstance(exc.stdout, str) else "",
                stderr=(exc.stderr or "") if isinstance(exc.stderr, str) else "",
                latency_ms=int((time.monotonic() - start) * 1000),
                timed_out=True,
            )


def extract_jsonrpc(stdout: str) -> list[dict[str, Any]]:
    """从混杂 stdout/logcat 文本中提取 JSON-RPC 对象。

    策略：逐行截取最外层 {} 片段尝试解析，保留含 jsonrpc/result/error
    键的对象。容忍日志行内嵌 JSON。
    """
    found: list[dict[str, Any]] = []
    for line in stdout.splitlines():
        line = line.strip()
        start = line.find("{")
        end = line.rfind("}")
        if start == -1 or end <= start:
            continue
        try:
            obj = json.loads(line[start : end + 1])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and {"jsonrpc", "result", "error"} & obj.keys():
            found.append(obj)
    return found


def build_test_config(case: dict[str, Any]) -> dict[str, Any]:
    """由单条用例生成车机 test_config 片段（参照 test_config_ark.json 结构）。

    覆盖 mcp_interface 的 tools_list / tools_call / resources_read；
    实际字段名待首次上机按自带客户端行为校准。
    """
    interface: dict[str, Any] = {"service_name": case["service"]}
    action = case["action"]
    if action == "tools_list":
        interface["test_tools_list"] = True
        interface["test_resources_list"] = True
    elif action == "tools_call":
        interface["test_tools_call"] = {
            "name": case["tool"],
            "arguments": case.get("arguments") or {},
        }
    elif action in ("resources_list", "resources_read"):
        interface["test_resources_list"] = True
        if case.get("tool"):
            interface["test_resources_read"] = [case["tool"]]
    else:
        raise ValueError(f"build_test_config 不支持 action={action}")
    return {"client_tests": {"mcp_interface": interface}}


def command_for_case(case: dict[str, Any], service_bin: str = "/data/local/tmp/mcp_eval/mcp_service") -> list[str]:
    """生成车机端执行命令。tools/call 经 -c -t --mcp <service> 触发配置中的用例。"""
    service = case["service"]
    return [service_bin, "-c", "-t", "--mcp", service]


RunnerFn = Callable[[list[str], int], AdbResult]


class DeviceChannel:
    """device 通道：经 adb 在车机执行用例，产出标准记录。"""

    def __init__(
        self,
        runner: RunnerFn,
        workdir: str = "/data/local/tmp/mcp_eval",
        config_target: str = "/aios/etc/test_config_ark.json",
    ) -> None:
        self.runner = runner
        self.workdir = workdir
        self.config_target = config_target

    def execute_case(
        self, case: dict[str, Any], run_id: str, timeout: int = 30
    ) -> EvalRecord:
        base = dict(
            run_id=run_id,
            case_id=case["case_id"],
            channel="device",
            action=case["action"],
            service=case["service"],
            tool=case.get("tool"),
            arguments=case.get("arguments"),
        )
        config = build_test_config(case)
        config_json = json.dumps(config, ensure_ascii=False)
        command = command_for_case(case)
        request_raw = {"command": command, "test_config": config}
        # 配置经 stdin 写入临时文件后执行；校准前不覆盖目标路径原件
        setup = (
            f"mkdir -p {self.workdir} && "
            f"cat > {self.workdir}/case_config.json <<'MCPEVAL_EOF'\n{config_json}\nMCPEVAL_EOF"
        )
        result = self.runner(["shell", setup], timeout)
        if result.timed_out or result.returncode != 0:
            return self._failure(base, result, "adb_setup_failed", request_raw)
        result = self.runner(["shell", " ".join(command)], timeout)
        return self.record_from_result(base, result, request_raw)

    def record_from_result(
        self, base: dict[str, Any], result: AdbResult, request_raw: dict[str, Any]
    ) -> EvalRecord:
        """把 adb 执行结果映射为标准记录（纯函数，离线可测）。"""
        if result.timed_out:
            return self._failure(base, result, "timeout", request_raw)
        records = extract_jsonrpc(result.stdout)
        response = records[-1] if records else None
        if result.returncode != 0:
            return self._failure(base, result, "exit_nonzero", request_raw, response)
        if response is None:
            return self._failure(base, result, "parse_failed", request_raw)
        return EvalRecord(
            **base,
            request_raw=request_raw,
            response_raw=response,
            execution_status="completed",
            latency_ms=result.latency_ms,
            stdout_tail=result.stdout[-2000:],
        )

    def _failure(
        self,
        base: dict[str, Any],
        result: AdbResult,
        category: str,
        request_raw: dict[str, Any] | None = None,
        response: dict[str, Any] | None = None,
    ) -> EvalRecord:
        status = "timeout" if category == "timeout" else "error"
        return EvalRecord(
            **base,
            request_raw=request_raw,
            response_raw=response,
            execution_status=status,
            error_category=category,
            latency_ms=result.latency_ms,
            stdout_tail=(result.stdout or "")[-2000:],
        )
