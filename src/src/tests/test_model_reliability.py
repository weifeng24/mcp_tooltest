"""任务预算与逐轮证据的独立回归。"""
from __future__ import annotations

import pytest

from mcp_eval.model_loop import ModelLoop
from mcp_eval.providers.base import ProviderError, ProviderResponse, ToolCallDecision
from mcp_eval.providers.openai_compat import OpenAICompatProvider
from mcp_eval.records import EvalRecord

TOOLS = [{"name": "service.setTemp", "inputSchema": {"type": "object",
          "properties": {"temperature": {"type": "integer"}}, "required": ["temperature"]}}]
CASE = {"case_id": "M01", "action": "model_task", "service": "auto", "task": "设置22度"}


class Executor:
    channel = "replay"
    source_type = "synthetic"

    def __init__(self):
        self.calls = []

    def __call__(self, name, arguments, *, timeout):
        self.calls.append((name, arguments, timeout))
        return EvalRecord(run_id="mock", case_id="adhoc", channel="replay", action="tools_call",
                          service="service", tool=name, arguments=arguments, trace_complete=True,
                          execution_status="completed", source_type="synthetic",
                          response_raw={"jsonrpc": "2.0", "id": 1, "result": {"isError": False}})


def test_no_dispatch_after_provider_consumes_deadline():
    clock = [0.0]

    class Slow:
        def chat(self, messages, tools, **kwargs):
            clock[0] = 999.0
            return ProviderResponse(tool_calls=[ToolCallDecision("a", "service_setTemp", {"temperature": 22})])

    executor = Executor()
    record = ModelLoop(Slow(), executor, TOOLS, max_rounds=1, clock=lambda: clock[0]).run_case(
        CASE, "run", "model", timeout_seconds=1)
    assert executor.calls == []
    assert record.execution_status == "timeout"


def test_tool_call_limit_is_distinct_from_round_limit():
    class Parallel:
        def chat(self, messages, tools, **kwargs):
            return ProviderResponse(tool_calls=[ToolCallDecision(str(i), "service_setTemp", {"temperature": 22})
                                                for i in range(2)])

    executor = Executor()
    result = ModelLoop(Parallel(), executor, TOOLS, max_tool_calls=1).run_case(CASE, "run", "model")
    assert len(executor.calls) == 1
    assert result.response_raw["stopped_reason"] == "max_tool_calls"


def test_usage_accumulates_all_turns_and_preserves_messages():
    class Script:
        index = 0

        def chat(self, messages, tools, **kwargs):
            self.index += 1
            if self.index == 1:
                return ProviderResponse(tool_calls=[ToolCallDecision("a", "service_setTemp", {"temperature": 22})],
                                        usage={"total_tokens": 20})
            return ProviderResponse(content="已设置22度", usage={"total_tokens": 30})

    record = ModelLoop(Script(), Executor(), TOOLS).run_case(CASE, "run", "model")
    assert record.response_raw["usage"]["total_tokens"] == 50
    assert record.response_raw["rounds"] == 2
    assert record.response_raw["call_count"] == 1
    assert record.latency_ms is not None
    assert len(record.events) >= 3
    assert record.request_raw["task"] == CASE["task"]


def test_null_provider_message_is_typed_failure():
    with pytest.raises(ProviderError):
        OpenAICompatProvider._parse({"choices": [{"message": None}]})


def test_non_object_tool_arguments_are_rejected():
    response = OpenAICompatProvider._parse({"choices": [{"message": {"tool_calls": [
        {"id": "a", "function": {"name": "service_setTemp", "arguments": "[]"}}]}}]})
    assert response.tool_calls[0].arguments_parse_error is not None


def test_unconfirmed_remote_call_does_not_claim_executed():
    class Provider:
        def chat(self, *args, **kwargs):
            return ProviderResponse(tool_calls=[ToolCallDecision("a", "service_setTemp", {"temperature": 22})])
    class Uncertain(Executor):
        def __call__(self, name, arguments, *, timeout):
            return EvalRecord(run_id="r", case_id="c", channel="replay", action="tools_call", service="service",
                              request_raw={"id": 1}, execution_status="timeout", trace_complete=False,
                              error_category="remote_state_unknown")
    result = ModelLoop(Provider(), Uncertain(), TOOLS).run_case(CASE, "run", "model")
    assert result.response_raw["tool_calls"][0]["executed"] is None
    assert result.execution_status == "error"
