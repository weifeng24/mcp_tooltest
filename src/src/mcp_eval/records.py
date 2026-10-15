"""标准评测记录：device 与 replay 双通道产出同一格式。

判定器只消费 EvalRecord，不感知记录来自真机还是回放。
回放记录单独以 channel 字段标记，报告中与真机数据分开统计。
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXECUTION_STATUSES = ["completed", "timeout", "error", "blocked", "not_run"]
VERDICTS = ["pass", "fail", "unassessed"]


@dataclass
class EvalRecord:
    """一条用例执行的标准记录。"""

    run_id: str
    case_id: str
    channel: str  # device | replay
    action: str
    service: str
    tool: str | None = None
    arguments: dict[str, Any] | None = None
    request_raw: dict[str, Any] | None = None
    response_raw: dict[str, Any] | None = None
    execution_status: str = "not_run"
    error_category: str | None = None
    latency_ms: int | None = None
    verdict: str | None = None  # 由判定器填写
    verdict_reason: str | None = None
    timestamp: str = ""
    stdout_tail: str = ""
    evidence: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        if self.execution_status not in EXECUTION_STATUSES:
            raise ValueError(f"非法 execution_status: {self.execution_status}")
        if self.verdict is not None and self.verdict not in VERDICTS:
            raise ValueError(f"非法 verdict: {self.verdict}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvalRecord":
        return cls(**data)


def request_signature(
    action: str, service: str, tool: str | None, arguments: dict[str, Any] | None
) -> str:
    """用例请求的稳定指纹，用于回放匹配。参数顺序不影响结果。"""
    payload = json.dumps(
        {"action": action, "service": service, "tool": tool, "arguments": arguments},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def append_jsonl(path: str | Path, record: EvalRecord) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"录制文件不存在: {p}")
    records = []
    for lineno, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{p}:{lineno} JSON 解析失败: {exc}") from exc
    return records
