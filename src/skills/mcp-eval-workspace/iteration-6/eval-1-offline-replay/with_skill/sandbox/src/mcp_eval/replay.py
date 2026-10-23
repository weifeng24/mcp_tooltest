"""顺序消费录制事件，保留源身份；未录制或已耗尽时返回 blocked。"""
from __future__ import annotations

from collections import defaultdict, deque
from pathlib import Path
from typing import Any

from .records import EvalRecord, read_jsonl, request_signature


class ReplayChannel:
    name = "replay"

    def __init__(self, recording_path: str | Path):
        self.recording_path = Path(recording_path)
        self._index = defaultdict(deque)
        sources = set()
        for index, raw in enumerate(read_jsonl(self.recording_path)):
            parent = EvalRecord.from_dict(raw)
            records = [parent] if parent.action != "model_task" else [
                EvalRecord.from_dict(call["record"]) for call in (parent.response_raw or {}).get("tool_calls", [])
                if isinstance(call, dict) and isinstance(call.get("record"), dict)]
            records.extend(EvalRecord.from_dict(value) for value in parent.provenance.get("postconditions", [])
                           if isinstance(value, dict) and "run_id" in value)
            for child_index, record in enumerate(records):
                signature = request_signature(record.action, record.service, record.tool, record.arguments)
                self._index[signature].append((f"{index}:{child_index}", record))
                sources.add(record.source_type)
        self.source_type = sources.pop() if len(sources) == 1 else "unknown"
        if self.source_type == "live_device":
            self.source_type = "recorded_device"

    def execute_case(self, case: dict[str, Any], run_id: str, timeout: float | None = None) -> EvalRecord:
        tool = case.get("resource_uri", case.get("tool")) if case["action"] == "resources_read" else case.get("tool")
        signature = request_signature(case["action"], case["service"], tool, case.get("arguments"))
        queue = self._index.get(signature)
        if not queue:
            return EvalRecord(run_id=run_id, case_id=case["case_id"], channel=self.name,
                              action=case["action"], service=case["service"], tool=tool,
                              arguments=case.get("arguments"), execution_status="blocked",
                              error_category="no_recording", source_type=self.source_type,
                              evidence=[str(self.recording_path)])
        index, source = queue.popleft()
        record = EvalRecord.from_dict(source.to_dict())
        record.run_id, record.case_id, record.channel = run_id, case["case_id"], self.name
        record.verdict, record.verdict_reason = None, None
        record.item_id, record.repeat_index = "", 0
        record.model = None
        record.source_type = "recorded_device" if source.source_type == "live_device" else source.source_type
        record.provenance = {**source.provenance, "source_run_id": source.run_id, "source_case_id": source.case_id,
                             "source_timestamp": source.timestamp, "source_event_index": index, "source_model": source.model}
        record.timestamp = EvalRecord(run_id=run_id, case_id=case["case_id"], channel=self.name,
                                      action=case["action"], service=case["service"]).timestamp
        record.evidence = [*record.evidence, str(self.recording_path)]
        return record
