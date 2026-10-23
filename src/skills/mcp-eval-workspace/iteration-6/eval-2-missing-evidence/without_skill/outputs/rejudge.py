"""离线复核本组缺失证据样本；只读输入，结果输出到标准输出。"""
import copy
import hashlib
import json
from pathlib import Path
import sys


root = Path.cwd()
inputs = [
    "fixtures/missing-evidence.json",
    "tests/cases/l2/M03_no_tool_needed.json",
    "src/mcp_eval/__init__.py",
    "src/mcp_eval/config.py",
    "src/mcp_eval/judge.py",
    "src/mcp_eval/records.py",
]


def hashes():
    return {
        name: hashlib.sha256((root / name).read_bytes()).hexdigest()
        for name in inputs
    }


before = hashes()
from mcp_eval.config import validate_config
from mcp_eval.judge import judge_record
from mcp_eval.records import EvalRecord

fixture = json.loads((root / inputs[0]).read_text(encoding="utf-8"))
case = json.loads((root / inputs[1]).read_text(encoding="utf-8"))
validate_config(case, "case", inputs[1])
assert fixture["case_id"] == case["case_id"]

# run_id/channel 是调用判定器所需的本地适配元数据，不代表执行过回放。
# fixture 未提供 events；空默认值不能作为完整事件证据。
record = EvalRecord(
    run_id="offline-fixture-recheck",
    case_id=fixture["case_id"],
    channel="replay",
    action=case["action"],
    service=case["service"],
    source_type=fixture["source_type"],
    execution_status=fixture["execution_status"],
    error_category=fixture["error_category"],
    trace_complete=fixture["trace_complete"],
    response_raw=copy.deepcopy(fixture["response_raw"]),
    verdict=fixture["verdict"],
)
judged = judge_record(case, record)
after = hashes()
assert before == after, "只读复核期间输入发生变化"
assert judged.verdict == "unassessed", judged.verdict
assert judged.verdict_reason == "执行或证据不完整: provider_error", judged.verdict_reason

print(json.dumps({
    "operation": "offline_judge_only",
    "fixture": inputs[0],
    "case": inputs[1],
    "case_id": fixture["case_id"],
    "assertions": case["assertions"],
    "source_type": fixture["source_type"],
    "execution_status": fixture["execution_status"],
    "error_category": fixture["error_category"],
    "trace_complete": fixture["trace_complete"],
    "tool_calls": fixture["response_raw"]["tool_calls"],
    "old_verdict": fixture["verdict"],
    "reviewed_verdict": judged.verdict,
    "reviewed_reason": judged.verdict_reason,
    "events_present_in_fixture": "events" in fixture,
    "adapter_metadata": {
        "run_id": "offline-fixture-recheck",
        "channel": "replay",
        "action_service_source": inputs[1],
        "events": "missing in fixture; dataclass default is not complete evidence",
        "execution": "judge only; no model, device or recording replay",
    },
    "input_sha256_before": before,
    "input_sha256_after": after,
    "inputs_unchanged": before == after,
    "imported_project_modules": sorted(
        str(Path(module.__file__).resolve().relative_to(root))
        for name, module in sys.modules.items()
        if name == "mcp_eval" or name.startswith("mcp_eval.")
    ),
}, ensure_ascii=False, indent=2))
