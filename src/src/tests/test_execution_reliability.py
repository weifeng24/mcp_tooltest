"""真实 CLI 契约与回放身份的回归（离线边界替身）。"""
import json
import shlex

from mcp_eval.device import AdbResult, DeviceChannel, command_for_case, extract_jsonrpc
from mcp_eval.records import EvalRecord, append_jsonl
from mcp_eval.replay import ReplayChannel

CASE = {"case_id": "P02", "action": "tools_call", "service": "auto",
        "tool": "HvacService.setTemp", "arguments": {"temperature": 22}}


def test_direct_command_carries_tool_and_arguments():
    command = command_for_case(CASE, "/system/bin/mcp_service")
    assert command[1:4] == ["-c", "-t", "--toolscall"]
    assert command[4] == CASE["tool"]
    assert json.loads(command[5]) == CASE["arguments"]


def test_no_argument_command_avoids_client_arg0_fallback():
    command = command_for_case({**CASE, "arguments": {}}, "mcp_service")
    assert command == ["mcp_service", "-c", "-t", "--toolscall", CASE["tool"]]


def test_request_echo_is_not_response():
    assert extract_jsonrpc('{"jsonrpc":"2.0","id":1,"method":"tools/call"}') == []


def test_multiline_json_response_is_preserved():
    response = {"jsonrpc": "2.0", "id": 1, "result": {"content": []}}
    assert extract_jsonrpc("Response: " + json.dumps(response, indent=2)) == [response]


def test_response_correlates_to_call_and_keeps_stderr():
    def runner(args, timeout):
        assert args[0] == "shell"
        assert "--toolscall" in shlex.split(args[1])
        return AdbResult(0, '{"jsonrpc":"2.0","id":1001,"result":{"wrong":true}}',
                         'Response: {"jsonrpc":"2.0","id":1,"result":{"correct":true}}', 9)

    record = DeviceChannel(runner).execute_case(CASE, "r")
    assert record.response_raw["id"] == 1
    assert record.stderr
    assert record.request_raw["params"]["arguments"] == CASE["arguments"]


def test_unverified_discovery_is_blocked_without_adb():
    def forbidden(*args):
        raise AssertionError("不应以 --mcp all 代替只读发现")

    record = DeviceChannel(forbidden).execute_case({**CASE, "action": "tools_list"}, "r")
    assert record.execution_status == "blocked"
    assert record.error_category == "unsupported_action"


def test_replay_preserves_order_and_current_identity(tmp_path):
    path = tmp_path / "source.jsonl"
    for ok in (False, True):
        append_jsonl(path, EvalRecord(run_id="source", case_id="P02", channel="device", action=CASE["action"],
                                     service=CASE["service"], tool=CASE["tool"], arguments=CASE["arguments"],
                                     execution_status="completed", trace_complete=True, source_type="synthetic",
                                     response_raw={"result": {"success": ok}}))
    replay = ReplayChannel(path)
    first = replay.execute_case({**CASE, "case_id": "P09"}, "new")
    second = replay.execute_case(CASE, "new")
    assert first.case_id == "P09"
    assert first.response_raw["result"]["success"] is False
    assert second.response_raw["result"]["success"] is True
    assert replay.execute_case(CASE, "new").execution_status == "blocked"
    assert first.provenance["source_case_id"] == "P02"


def test_real_result_postconditions_can_be_replayed(tmp_path):
    path = tmp_path / "captured-results.jsonl"
    readback = EvalRecord(run_id="source", case_id="P02", channel="device", action="tools_call",
                          service="auto", tool="HvacService.getTemp", arguments={}, trace_complete=True,
                          source_type="live_device", execution_status="completed",
                          response_raw={"result": {"structuredContent": {"temperature": 22}}})
    primary = EvalRecord(run_id="source", case_id="P02", channel="device", action=CASE["action"],
                         service=CASE["service"], tool=CASE["tool"], arguments=CASE["arguments"],
                         trace_complete=True, source_type="live_device", execution_status="completed",
                         response_raw={"result": {"isError": False}},
                         provenance={"postconditions": [readback.to_dict()]})
    append_jsonl(path, primary)
    replay = ReplayChannel(path)
    replay.execute_case(CASE, "new")
    result = replay.execute_case({**CASE, "tool": "HvacService.getTemp", "arguments": {}}, "new")
    assert result.execution_status == "completed"
    assert result.response_raw["result"]["structuredContent"]["temperature"] == 22
    assert result.source_type == "recorded_device"
