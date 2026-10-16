"""L2 模型决策循环的单元测试（脚本化 provider + mock 执行器，不调真实 API）。"""
from __future__ import annotations

import pytest

from mcp_eval.judge import judge_record
from mcp_eval.model_loop import ModelLoop
from mcp_eval.providers.base import ProviderError, ProviderResponse, ToolCallDecision

TOOLS = [
    {
        "name": "16777217.setTemp",
        "description": "设置空调温度",
        "inputSchema": {
            "type": "object",
            "properties": {
                "temperature": {"type": "integer", "minimum": 16, "maximum": 30}
            },
            "required": ["temperature"],
        },
    },
    {
        "name": "16777217.getTemp",
        "description": "获取空调温度",
        "inputSchema": {"type": "object", "properties": {}},
    },
]

CASE_M01 = {
    "case_id": "M01",
    "level": "L2",
    "category": "positive",
    "service": "auto",
    "action": "model_task",
    "task": "把空调温度调到 22 度",
    "assertions": [
        {"type": "model_selects_tool", "name_contains": "setTemp"},
        {"type": "max_rounds", "value": 3},
    ],
}


class ScriptedProvider:
    """按脚本依次返回响应（或抛出异常）的假 provider。"""

    def __init__(self, script: list) -> None:
        self.script = list(script)
        self.requests: list[list[dict]] = []

    def chat(self, messages, tools):
        self.requests.append(list(messages))
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class MockExecutor:
    channel = "replay"

    def __init__(self, handler) -> None:
        self.handler = handler
        self.calls: list[tuple[str, dict]] = []

    def __call__(self, name: str, arguments: dict) -> dict:
        self.calls.append((name, arguments))
        return self.handler(name, arguments)


def decide(name: str, args: dict, call_id: str = "c1") -> ProviderResponse:
    return ProviderResponse(tool_calls=[ToolCallDecision(call_id=call_id, name=name, arguments=args)])


def answer(text: str) -> ProviderResponse:
    return ProviderResponse(content=text)


def ok_result(**extra) -> dict:
    return {"content": [{"type": "text", "text": "ok"}], "success": True, **extra}


def success_executor(name: str, arguments: dict) -> dict:
    return ok_result()


# ---------- 主流程 ----------


def test_happy_path_complete_and_judge_pass():
    provider = ScriptedProvider([
        decide("16777217.setTemp", {"temperature": 22}),
        answer("已将空调温度调到 22 度"),
    ])
    loop = ModelLoop(provider, MockExecutor(success_executor), TOOLS, max_rounds=5)
    record = loop.run_case(CASE_M01, "run1", "deepseek-chat")

    assert record.execution_status == "completed"
    assert record.response_raw["stopped_reason"] == "final_answer"
    assert record.response_raw["rounds"] == 1
    assert record.response_raw["tool_calls"][0]["name"] == "16777217.setTemp"
    assert record.response_raw["tool_calls"][0]["arguments"] == {"temperature": 22}
    assert "22" in record.response_raw["final_answer"]
    # 工具结果确实回填给了模型（第二轮请求里包含 role=tool 消息）
    assert any(m.get("role") == "tool" for m in provider.requests[1])

    judged = judge_record(CASE_M01, record)
    assert judged.verdict == "pass"


def test_max_rounds_forces_stop():
    provider = ScriptedProvider([decide("16777217.getTemp", {})] * 10)
    loop = ModelLoop(provider, MockExecutor(success_executor), TOOLS, max_rounds=3)
    record = loop.run_case(CASE_M01, "run1", "deepseek-chat")
    assert record.execution_status == "completed"
    assert record.response_raw["stopped_reason"] == "max_rounds"
    assert record.response_raw["rounds"] == 3
    # 超轮在用例断言下应判 fail（上限 3，实际 3 轮内未给最终回答）
    case = {**CASE_M01, "assertions": [{"type": "max_rounds", "value": 2}]}
    assert judge_record(case, record).verdict == "fail"


def test_timeout_forces_stop():
    clock_time = [0.0]

    class SlowProvider:
        def chat(self, messages, tools):
            clock_time[0] += 999.0
            return decide("16777217.getTemp", {})

    loop = ModelLoop(SlowProvider(), MockExecutor(success_executor), TOOLS,
                     clock=lambda: clock_time[0])
    record = loop.run_case(CASE_M01, "run1", "deepseek-chat", timeout_seconds=120)
    assert record.execution_status == "timeout"
    assert record.error_category == "timeout"


def test_provider_error_recorded():
    provider = ScriptedProvider([ProviderError("HTTP 401: invalid key")])
    loop = ModelLoop(provider, MockExecutor(success_executor), TOOLS)
    record = loop.run_case(CASE_M01, "run1", "deepseek-chat")
    assert record.execution_status == "error"
    assert record.error_category == "provider_error"
    assert "401" in record.response_raw["error_detail"]


# ---------- 自我纠正回填 ----------


def test_unknown_tool_fed_back_and_counted():
    provider = ScriptedProvider([
        decide("16777217.openSunroof", {}),
        answer("好的"),
    ])
    loop = ModelLoop(provider, MockExecutor(success_executor), TOOLS)
    record = loop.run_case(CASE_M01, "run1", "deepseek-chat")
    assert record.execution_status == "completed"
    assert record.response_raw["validation_errors"] == 1
    bad_call = record.response_raw["tool_calls"][0]
    assert bad_call["result"]["isError"] is True
    assert "未知工具" in bad_call["result"]["content"][0]["text"]


def test_schema_violation_fed_back_not_executed():
    executor = MockExecutor(success_executor)
    provider = ScriptedProvider([
        decide("16777217.setTemp", {"temperature": 40}),  # 越界
        answer("已调整"),
    ])
    loop = ModelLoop(provider, executor, TOOLS)
    record = loop.run_case(CASE_M01, "run1", "deepseek-chat")
    assert record.response_raw["validation_errors"] == 1
    assert executor.calls == []  # 校验失败的参数不会真正下发执行
    assert "inputSchema" in record.response_raw["tool_calls"][0]["result"]["content"][0]["text"]


def test_executor_exception_becomes_tool_error_not_crash():
    def broken(name, arguments):
        raise RuntimeError("dds 通道断开")

    provider = ScriptedProvider([decide("16777217.getTemp", {}), answer("工具暂时不可用")])
    loop = ModelLoop(provider, MockExecutor(broken), TOOLS)
    record = loop.run_case(CASE_M01, "run1", "deepseek-chat")
    assert record.execution_status == "completed"
    assert record.response_raw["tool_calls"][0]["result"]["isError"] is True
    assert record.response_raw["validation_errors"] == 0  # 执行异常不算校验错误


# ---------- provider 解析与工厂 ----------


def test_openai_response_parse_tool_calls():
    from mcp_eval.providers.openai_compat import OpenAICompatProvider

    raw = {
        "choices": [{
            "message": {
                "content": None,
                "tool_calls": [{
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "16777217.setTemp", "arguments": '{"temperature": 22}'},
                }],
            }
        }],
        "usage": {"total_tokens": 42},
    }
    resp = OpenAICompatProvider._parse(raw)
    assert resp.tool_calls[0].name == "16777217.setTemp"
    assert resp.tool_calls[0].arguments == {"temperature": 22}
    assert resp.usage["total_tokens"] == 42


def test_openai_response_parse_bad_arguments_tolerated():
    from mcp_eval.providers.openai_compat import OpenAICompatProvider

    raw = {"choices": [{"message": {"tool_calls": [
        {"id": "c", "function": {"name": "t", "arguments": "{bad json"}}
    ]}}]}
    resp = OpenAICompatProvider._parse(raw)
    assert resp.tool_calls[0].arguments_parse_error is not None


def test_mcp_tools_to_openai_conversion():
    from mcp_eval.providers.openai_compat import OpenAICompatProvider

    converted = OpenAICompatProvider.mcp_tools_to_openai(TOOLS)
    assert converted[0]["function"]["name"] == "16777217.setTemp"
    assert converted[0]["function"]["parameters"]["required"] == ["temperature"]


def test_create_provider_requires_env_key(monkeypatch):
    from mcp_eval.providers import create_provider

    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    config = {"provider": "deepseek", "model": "deepseek-chat", "api_key_env": "DEEPSEEK_API_KEY"}
    with pytest.raises(ProviderError, match="DEEPSEEK_API_KEY"):
        create_provider(config)


def test_create_provider_uses_default_base_url(monkeypatch):
    from mcp_eval.providers import create_provider

    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    config = {"provider": "deepseek", "model": "deepseek-chat",
              "api_key_env": "DEEPSEEK_API_KEY", "generation": {"temperature": 0.0}}
    provider = create_provider(config)
    assert provider.base_url == "https://api.deepseek.com"
    assert provider.model == "deepseek-chat"
