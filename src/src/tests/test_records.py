"""标准记录与请求指纹的单元测试。"""
from __future__ import annotations

import pytest

from mcp_eval.records import (
    EvalRecord,
    append_jsonl,
    read_jsonl,
    request_signature,
)


def make_record(**overrides) -> EvalRecord:
    base = dict(
        run_id="r1",
        case_id="P02",
        channel="device",
        action="tools_call",
        service="auto",
        tool="HvacService.setTemp",
        arguments={"temperature": 22},
    )
    return EvalRecord(**{**base, **overrides})


def test_timestamp_auto_filled():
    assert make_record().timestamp != ""


def test_invalid_execution_status_rejected():
    with pytest.raises(ValueError, match="execution_status"):
        make_record(execution_status="done")


def test_invalid_verdict_rejected():
    with pytest.raises(ValueError, match="verdict"):
        make_record(verdict="ok")


def test_signature_ignores_argument_order():
    a = request_signature("tools_call", "auto", "t", {"x": 1, "y": 2})
    b = request_signature("tools_call", "auto", "t", {"y": 2, "x": 1})
    assert a == b


def test_signature_changes_with_arguments():
    a = request_signature("tools_call", "auto", "t", {"x": 1})
    b = request_signature("tools_call", "auto", "t", {"x": 2})
    assert a != b


def test_jsonl_round_trip(tmp_path):
    f = tmp_path / "rec.jsonl"
    append_jsonl(f, make_record(response_raw={"result": {"success": True}}))
    append_jsonl(f, make_record(case_id="N01", execution_status="completed"))
    records = read_jsonl(f)
    assert len(records) == 2
    assert records[0]["response_raw"]["result"]["success"] is True
    assert records[1]["case_id"] == "N01"


def test_read_jsonl_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_jsonl(tmp_path / "none.jsonl")


def test_read_jsonl_bad_line(tmp_path):
    f = tmp_path / "bad.jsonl"
    f.write_text('{"ok": 1}\n{bad\n', encoding="utf-8")
    with pytest.raises(ValueError, match="2"):
        read_jsonl(f)
