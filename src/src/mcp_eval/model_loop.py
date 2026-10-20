"""L2 模型循环：共享任务截止时间，区分决策、执行和后置验证证据。"""
from __future__ import annotations

import copy
import json
import re
import time
from typing import Any, Callable, Protocol

import jsonschema

from .config import validate_tools
from .providers.base import ProviderError, ProviderResponse, ToolCallDecision
from .providers.openai_compat import OpenAICompatProvider
from .records import EvalRecord

SYSTEM_PROMPT = (
    "你是车载智能助手，可调用提供的工具完成任务。只在必要时调用工具，"
    "参数须符合工具约束；信息不足时先澄清。根据实际工具结果回答，不声称未完成的操作已经成功。"
)


class ToolNameMapper:
    """将 MCP 工具名映射为互不冲突的 API 名，执行时恢复原始名称。"""

    def __init__(self, names: list[str]):
        self.to_api, self.to_mcp = {}, {}
        for original in names:
            if original in self.to_api:
                raise ValueError(f"重复工具名: {original}")
            safe = re.sub(r"[^a-zA-Z0-9_-]", "_", original)[:64] or "tool"
            candidate, index = safe, 1
            while candidate in self.to_mcp:
                index += 1
                suffix = f"_{index}"
                candidate = safe[:64 - len(suffix)] + suffix
            self.to_api[original], self.to_mcp[candidate] = candidate, original


class ToolExecutor(Protocol):
    channel: str
    source_type: str

    def __call__(self, name: str, arguments: dict[str, Any], *, timeout: float) -> EvalRecord: ...


class ModelLoop:
    def __init__(self, provider, executor: ToolExecutor, tools: list[dict[str, Any]], *,
                 max_rounds: int = 5, max_tool_calls: int = 10,
                 clock: Callable[[], float] = time.monotonic):
        if max_rounds < 1 or max_tool_calls < 1:
            raise ValueError("调用上限必须大于零")
        self.provider, self.executor, self.clock = provider, executor, clock
        self.tools = {tool["name"]: tool for tool in validate_tools(tools)}
        self.name_map = ToolNameMapper(list(self.tools))
        self.openai_tools = OpenAICompatProvider.mcp_tools_to_openai(tools, self.name_map.to_api)
        self.max_rounds, self.max_tool_calls = max_rounds, max_tool_calls

    def run_case(self, case: dict[str, Any], run_id: str, model_config_id: str,
                 timeout_seconds: float = 120, *, checkpoint: Callable[[EvalRecord], None] | None = None) -> EvalRecord:
        """同步运行；可选checkpoint在请求/执行边界保存快照，异常由编排层收尾。"""
        checkpoint = checkpoint or (lambda record: None)
        start = self.clock()
        budget = min(timeout_seconds, case.get("timeout_seconds", timeout_seconds))
        deadline = start + budget
        record = EvalRecord(run_id=run_id, case_id=case["case_id"], channel=self.executor.channel,
                             action="model_task", service=case["service"], model=model_config_id,
                             execution_status="error", error_category="execution_in_progress",
                            source_type=getattr(self.executor, "source_type", "unknown"))
        messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": case["task"]}]
        record.request_raw = {"task": case["task"], "tools": copy.deepcopy(list(self.tools.values())),
                              "api_name_map": self.name_map.to_api, "messages": messages}
        record.response_raw = {"tool_calls": [], "final_answer": None, "rounds": 0,
                               "call_count": 0, "validation_errors": 0, "usage_by_round": []}
        data = record.response_raw
        complete = True
        checkpoint(record)

        def finish(reason, status="completed", error=None):
            record.execution_status, record.error_category = status, error
            record.latency_ms = max(0, int((self.clock() - start) * 1000))
            record.trace_complete = complete
            data["stopped_reason"] = reason
            data["call_count"] = len(data["tool_calls"])
            usage = data["usage_by_round"]
            data["usage"] = {key: sum(row[key] for row in usage) if usage and all(
                isinstance(row, dict) and type(row.get(key)) is int for row in usage) else None
                 for key in ("prompt_tokens", "completion_tokens", "total_tokens")}
            checkpoint(record)
            return record

        for _ in range(self.max_rounds):
            remaining = deadline - self.clock()
            if remaining <= 0:
                return finish("timeout", "timeout", "timeout")
            record.events.append({"kind": "model_request", "messages": copy.deepcopy(messages)})
            data["rounds"] += 1
            checkpoint(record)
            remaining = deadline - self.clock()
            if remaining <= 0:
                complete = False
                return finish("timeout", "timeout", "timeout")
            try:
                response = self.provider.chat(messages, self.openai_tools, timeout=remaining)
            except ProviderError as exc:
                complete = False
                record.events.append({"kind": "provider_error", "message": str(exc)})
                data["error_detail"] = str(exc)
                return finish("provider_error", "error", "provider_error")
            data["usage_by_round"].append(response.usage)
            record.events.append({"kind": "model_response", "raw": response.raw,
                                  "content": response.content, "finish_reason": response.finish_reason,
                                   "decisions": [vars(decision).copy() for decision in response.tool_calls]})
            checkpoint(record)
            if self.clock() >= deadline:
                complete = False
                return finish("timeout", "timeout", "timeout")
            if response.finish_reason not in (None, "stop", "tool_calls"):
                complete = False
                return finish("incomplete_response", "error", "incomplete_response")
            if not response.tool_calls:
                if not isinstance(response.content, str) or not response.content.strip():
                    complete = False
                    return finish("empty_answer", "error", "incomplete_response")
                messages.append({"role": "assistant", "content": response.content})
                data["final_answer"] = response.content
                checks = []
                record.provenance["postconditions"] = checks
                checkpoint(record)
                for expected in case.get("postconditions", []):
                    if self.clock() >= deadline:
                        complete = False
                        return finish("timeout", "timeout", "timeout")
                    try:
                        record.events.append({"kind": "postcondition_started", "tool": expected["tool"],
                                              "arguments": expected["arguments"]})
                        checkpoint(record)
                        if self.clock() >= deadline:
                            complete = False
                            return finish("timeout", "timeout", "timeout")
                        checked = self.executor(expected["tool"], expected["arguments"],
                                                timeout=deadline - self.clock())
                        checks.append(checked.to_dict())
                        record.events.append({"kind": "postcondition", "record": checked.to_dict()})
                    except (OSError, ValueError, RuntimeError) as exc:
                        checks.append({"trace_complete": False, "error": str(exc)})
                    checkpoint(record)
                    if self.clock() >= deadline:
                        complete = False
                        return finish("timeout", "timeout", "timeout")
                return finish("final_answer")
            messages.append(self._assistant_message(response))
            for decision in response.tool_calls:
                if len(data["tool_calls"]) >= self.max_tool_calls:
                    return finish("max_tool_calls")
                if self.clock() >= deadline:
                    complete = False
                    return finish("timeout", "timeout", "timeout")
                name = self.name_map.to_mcp.get(decision.name, decision.name)
                call = {"name": name, "api_name": decision.name, "arguments": decision.arguments,
                        "call_id": decision.call_id, "executed": False, "execution_status": "not_run"}
                data["tool_calls"].append(call)
                problem = self._validate_decision(decision, name)
                if problem:
                    data["validation_errors"] += 1
                    call["result"] = _tool_error(problem)
                    call["validation_error"] = problem
                else:
                    try:
                        call["executed"] = None  # 已准备下发；中断时不能断言远端未执行。
                        call["execution_status"] = "error"
                        checkpoint(record)
                        if self.clock() >= deadline:
                            call["executed"], call["execution_status"] = False, "not_run"
                            complete = False
                            return finish("timeout", "timeout", "timeout")
                        executed = self.executor(name, decision.arguments, timeout=deadline - self.clock())
                        call["record"] = executed.to_dict()
                        call["executed"] = (True if executed.trace_complete and executed.execution_status == "completed"
                                            else None if executed.request_raw is not None else False)
                        call["execution_status"] = executed.execution_status
                        raw = executed.response_raw or {}
                        call["result"] = raw.get("result", raw)
                        record.events.append({"kind": "tool_execution", "record": executed.to_dict()})
                        checkpoint(record)
                        if executed.execution_status != "completed" or not executed.trace_complete:
                            complete = False
                            return finish("executor_error", "error", executed.error_category or "executor_error")
                    except (OSError, ValueError, RuntimeError) as exc:
                        complete = False
                        call["executed"] = None  # 异常不证明远端完全未执行。
                        call["result"] = _tool_error(str(exc))
                        return finish("executor_error", "error", "executor_error")
                if self.clock() >= deadline:
                    complete = False
                    return finish("timeout", "timeout", "timeout")
                messages.append({"role": "tool", "tool_call_id": decision.call_id,
                                 "content": json.dumps(call["result"], ensure_ascii=False)})
        return finish("max_rounds")

    def _validate_decision(self, decision: ToolCallDecision, name: str) -> str | None:
        if decision.arguments_parse_error:
            return decision.arguments_parse_error
        if name not in self.tools:
            return f"未知工具 {name}"
        try:
            jsonschema.validate(decision.arguments, self.tools[name]["inputSchema"])
        except jsonschema.ValidationError as exc:
            return f"参数不满足 inputSchema: {exc.message}"
        return None

    @staticmethod
    def _assistant_message(response: ProviderResponse) -> dict[str, Any]:
        return {"role": "assistant", "content": response.content,
                "tool_calls": [{"id": d.call_id, "type": "function", "function": {
                    "name": d.name, "arguments": d.arguments_raw if d.arguments_raw is not None
                    else json.dumps(d.arguments, ensure_ascii=False)}} for d in response.tool_calls]}


def _tool_error(message: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": message}], "isError": True}
