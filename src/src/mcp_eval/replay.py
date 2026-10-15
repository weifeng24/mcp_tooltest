"""回放通道：读取录制的标准记录，离线复现执行结果。

录制文件为 JSONL（每行一条 EvalRecord）。按请求指纹匹配；
匹配不到时返回 blocked/no_recording，绝不伪造结果。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .records import EvalRecord, read_jsonl, request_signature


class ReplayChannel:
    def __init__(self, recording_path: str | Path) -> None:
        self.recording_path = Path(recording_path)
        self._index: dict[str, dict[str, Any]] = {}
        for raw in read_jsonl(self.recording_path):
            record = EvalRecord.from_dict(raw)
            sig = request_signature(
                record.action, record.service, record.tool, record.arguments
            )
            # 同一请求多次录制时以最后一条为准（后录制的更新）
            self._index[sig] = raw

    def execute_case(self, case: dict[str, Any], run_id: str) -> EvalRecord:
        sig = request_signature(
            case["action"], case["service"], case.get("tool"), case.get("arguments")
        )
        hit = self._index.get(sig)
        if hit is None:
            return EvalRecord(
                run_id=run_id,
                case_id=case["case_id"],
                channel="replay",
                action=case["action"],
                service=case["service"],
                tool=case.get("tool"),
                arguments=case.get("arguments"),
                execution_status="blocked",
                error_category="no_recording",
                evidence=[str(self.recording_path)],
            )
        record = EvalRecord.from_dict(hit)
        record.run_id = run_id
        record.channel = "replay"
        record.timestamp = ""
        record.__post_init__()
        record.evidence = list(record.evidence) + [str(self.recording_path)]
        return record
