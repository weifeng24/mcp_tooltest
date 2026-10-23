"""只读采集服务注册时的定义快照；不执行工具、不声称实时发现已通过。

依据 Ark RouteManager.cpp:852-858/927-933：dump 保存原始 service_tools/
service_resources。未带点号的工具名使用 CLI 支持的 serviceName.method 别名，
不从旧版 --svcmap 文档猜测数值 serviceId。
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import re
import shlex
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from .config import ConfigError, validate_tools
from .device import AdbRunner


def _service_name(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}", value):
        raise ConfigError("服务名格式不适合定义快照文件")
    return value


def _definition_list(raw: Any, kind: str) -> list[dict]:
    if not isinstance(raw, dict):
        raise ConfigError("定义快照必须为JSON对象")
    data = raw.get("response", raw)
    if isinstance(data, dict):
        data = data.get("result", data)
    values = data.get(kind) if isinstance(data, dict) else None
    if not isinstance(values, list) or any(not isinstance(value, dict) for value in values):
        raise ConfigError(f"未找到完整 {kind} 数组；摘要日志不能代替定义")
    return values


def normalize_tools_snapshot(service: str, raw: dict) -> tuple[list[dict], list[dict]]:
    """保留原定义，产生可用于L2配置的服务名别名及显式映射证据。"""
    service = _service_name(service)
    tools = copy.deepcopy(_definition_list(raw, "tools"))
    bindings = []
    for tool in tools:
        name = tool.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ConfigError("工具定义缺少名称")
        normalized = name if "." in name else f"{service}.{name}"
        tool["name"] = normalized
        bindings.append({"service": service, "original_name": name, "normalized_name": normalized,
                         "name_policy": "preserve_dotted_else_service_name_alias",
                         "alias_verified_on_device": False})
    if tools:
        validate_tools(tools, service)
    return tools, bindings


def catalog_plan(server: dict, services: list[str] | None = None) -> list[dict]:
    selected = services if services is not None else server["services"]
    if not selected or len(selected) != len(set(selected)):
        raise ConfigError("采集服务列表不能为空或重复")
    directory = server.get("dump_dir")
    if (not isinstance(directory, str) or not directory.startswith("/")
            or ".." in PurePosixPath(directory).parts or any(c in directory for c in "\x00\n\r")):
        raise ConfigError("需配置已核实的绝对 dump_dir，不得包含上级目录或控制字符")
    planned = []
    for service in selected:
        _service_name(service)
        if service not in server["services"]:
            raise ConfigError(f"服务不在server配置范围内: {service}")
        for kind in ("tools", "resources"):
            filename = f"{kind}_{service}.json"
            remote = str(PurePosixPath(directory) / filename)
            planned.append({"service": service, "kind": kind, "filename": filename, "remote": remote,
                            "argv": ["shell", shlex.join(["cat", remote])]})
    return planned


def _save(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def capture_catalog(server: dict, root: str | Path, *, services: list[str] | None = None,
                    runner=None, timeout: float = 120) -> dict:
    planned = catalog_plan(server, services)
    if not server.get("device_serial", "").strip():
        raise ConfigError("采集前必须填写 device_serial")
    if not math.isfinite(timeout) or timeout <= 0:
        raise ConfigError("timeout必须为有限正数")
    root = Path(root).resolve()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    directory = root / "tests/results" / f"catalog-capture-{stamp}-{uuid.uuid4().hex[:8]}"
    if not directory.resolve().is_relative_to(root):
        raise ConfigError("采集输出目录超出交付区")
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "raw").mkdir()
    runner = runner or AdbRunner(serial=server["device_serial"])
    manifest = {"schema_version": 1, "source": {"kind": "registration_dump", "device_serial": server["device_serial"],
                "server_id": server["server_id"], "dump_dir": server["dump_dir"], "captured_at": stamp,
                "scope": "requested_services_only", "requested_services": services or server["services"],
                "freshness": "not_verified", "atomic_snapshot": False,
                "runtime_tools_list_tested": False, "resource_values_read": False},
                "files": [{**item, "status": "not_run"} for item in planned]}
    tools, bindings, resources, names = [], [], {}, set()
    interrupted = False
    deadline = time.monotonic() + timeout
    _save(directory / "capture_manifest.json", manifest)
    try:
        for item in manifest["files"]:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                item["reason"] = "capture_deadline"
                continue
            try:
                result = runner(item["argv"], remaining)
                text_path = directory / "raw" / (item["filename"] + ".stdout.txt")
                error_path = directory / "raw" / (item["filename"] + ".stderr.txt")
                text_path.write_text(result.stdout, encoding="utf-8")
                error_path.write_text(result.stderr, encoding="utf-8")
                item.update(stdout=str(text_path.relative_to(directory)), stderr=str(error_path.relative_to(directory)),
                            returncode=result.returncode, latency_ms=result.latency_ms,
                            captured_text_sha256=hashlib.sha256(result.stdout.encode()).hexdigest())
                if result.timed_out or result.returncode:
                    item.update(status="error", reason="read_timeout" if result.timed_out else "read_failed")
                else:
                    raw = json.loads(result.stdout)
                    if item["kind"] == "tools":
                        subset, mapped = normalize_tools_snapshot(item["service"], raw)
                        if any(tool["name"] in names for tool in subset):
                            raise ConfigError("不同服务的完整工具名冲突，不能静默覆盖")
                        names.update(tool["name"] for tool in subset)
                        tools.extend(subset)
                        bindings.extend(mapped)
                    else:
                        resources[item["service"]] = _definition_list(raw, "resources")
                    _save(directory / "raw" / item["filename"], raw)
                    item.update(status="captured", parsed=str(Path("raw") / item["filename"]))
            except (OSError, ValueError, TypeError) as exc:
                item.update(status="error", reason=f"{type(exc).__name__}: {exc}")
            _save(directory / "capture_manifest.json", manifest)
    except KeyboardInterrupt:
        interrupted = True
    finally:
        complete = all(item["status"] == "captured" for item in manifest["files"])
        tools_complete = all(item["status"] == "captured" for item in manifest["files"] if item["kind"] == "tools")
        state = "complete" if complete else "partial" if any(i["status"] == "captured" for i in manifest["files"]) else "failed"
        manifest.update(state="interrupted" if interrupted else "finished", catalog_status=state)
        catalog = {"schema_version": 1, "catalog_status": state, "tools_status": "complete" if tools_complete else "partial",
                   "source": manifest["source"], "tools": tools, "bindings": bindings,
                   "resources_by_service": resources, "capture_manifest": "capture_manifest.json",
                   "warnings": ["注册文件可能陈旧，采集不证明当前注册状态、实时工具发现或资源值读取。",
                                "未加前缀的名称使用服务名别名，须在最小调用中验证；未猜测数值serviceId。"]}
        _save(directory / "capture_manifest.json", manifest)
        _save(directory / "catalog.json", catalog)
    return {"catalog_status": state, "tools_status": catalog["tools_status"], "tools_count": len(tools),
            "interrupted": interrupted, "catalog": str((directory / "catalog.json").relative_to(root)),
            "manifest": str((directory / "capture_manifest.json").relative_to(root)),
            "runtime_tools_list_tested": False, "resource_values_read": False}
