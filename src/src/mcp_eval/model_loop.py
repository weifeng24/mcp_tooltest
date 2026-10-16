"""L2 模型决策循环：模型选工具 → 校验 → 执行 → 回填 → 直到最终回答。

约束与安全：
- 最大轮数与总超时强约束，防止无限调用
- 参数先按工具的 inputSchema 校验；校验失败作为工具错误回填给模型自我纠正
- 模型调用未知工具同样作为工具错误回填，不中断循环
- 模型只见到任务与工具定义，不接触用例预期
"""
from __future__ import annotations

import json
import re
import time
from typing import Any, Callable, Protocol

import jsonschema

from .providers.base import ProviderError, ToolCallDecision
from .providers.openai_compat import OpenAICompatProvider
from .records import EvalRecord

SYSTEM_PROMPT = (
    "你是车载智能助手。用户会提出与车辆相关的任务，你可以调用提供的 MCP 工具完成。"
    "只在确有必要时调用工具；参数必须符合工具的 inputSchema。"
    "任务完成后用中文简要回答结果。"
)


class ToolNameMapper:
    """MCP 工具名 ↔ API 安全名的双向映射。

    OpenAI 兼容 API 的函数名须满足 ^[a-zA-Z0-9_-]{1,64}$，而公司 MCP 工具名
    形如 16777217.setTemp（含点号）。映射冲突时追加序号；证据中保留原始名。
    """

    def __init__(self, names: list[str]) -> None:
        self.to_api: dict[str, str] = {}
        self.to_mcp: dict[str, str] = {}
        used: set[str] = set()
        for original in names:
            safe = re.sub(r"[^a-zA-Z0-9_-]", "_", original)[:64] or "tool"
            candidate, suffix = safe, 1
            while candidate in used:
                suffix += 1
                candidate = f"{safe[:60]}_{suffix}"
            used.add(candidate)
            self.to_api[original] = candidate
            self.to_mcp[candidate] = original


class ToolExecutor(Protocol):
    """工具执行器协议：device / replay / mock 均按此接入。"""

    channel: str

    def __call__(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """执行工具调用，返回 MCP 风格的 tool result。"""
        ...


ClockFn = Callable[[], float]


class ModelLoop:
    def __init__(
        self,
        provider: Any,
        executor: ToolExecutor,
        tools: list[dict[str, Any]],
        *,
        max_rounds: int = 5,
        clock: ClockFn = time.monotonic,
    ) -> None:
        self.provider = provider
        self.executor = executor
        self.tools = {t["name"]: t for t in tools}
        self.name_map = ToolNameMapper(list(self.tools))
        self.openai_tools = OpenAICompatProvider.mcp_tools_to_openai(tools, self.name_map.to_api)
        self.max_rounds = max_rounds
        self.clock = clock

    def run_case(
        self,
        case: dict[str, Any],
        run_id: str,
        model_config_id: str,
        timeout_seconds: int = 120,
    ) -> EvalRecord:
        base = dict(
            run_id=run_id,
            case_id=case["case_id"],
            channel=getattr(self.executor, "channel", "unknown"),
            action=case["action"],
            service=case["service"],
            model=model_config_id,
        )
        start = self.clock()
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": case["task"]},
        ]
        call_log: list[dict[str, Any]] = []
        validation_errors = 0
        usage: dict[str, Any] | None = None

        for _round in range(1, self.max_rounds + 1):
            if self.clock() - start > timeout_seconds:
                return self._finish(base, call_log, None, "timeout", validation_errors,
                                    usage, execution_status="timeout",
                                    error_category="timeout")
            try:
                response = self.provider.chat(messages, self.openai_tools)
            except ProviderError as exc:
                return self._finish(base, call_log, None, "provider_error",
                                    validation_errors, usage,
                                    execution_status="error",
                                    error_category="provider_error",
                                    error_detail=str(exc))
            if response.usage:
                usage = response.usage
            if not response.tool_calls:
                return self._finish(base, call_log, response.content, "final_answer",
                                    validation_errors, usage)
            messages.append(self._assistant_message(response))
            for decision in response.tool_calls:
                original_name = self.name_map.to_mcp.get(decision.name, decision.name)
                result, is_validation_error = self._execute_decision(decision, original_name)
                if is_validation_error:
                    validation_errors += 1
                call_log.append(
                    {
                        "name": original_name,
                        "api_name": decision.name,
                        "arguments": decision.arguments,
                        "result": result,
                    }
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": decision.call_id,
                        "content": json.dumps(result, ensure_ascii=False),
                    }
                )
        return self._finish(base, call_log, None, "max_rounds", validation_errors, usage)

    def _execute_decision(
        self, decision: ToolCallDecision, original_name: str
    ) -> tuple[dict[str, Any], bool]:
        """执行一次工具调用决策；返回 (tool_result, 是否为校验类错误)。

        original_name 为映射回 MCP 侧的原始工具名（执行与证据均用原始名）。
        """
        if decision.arguments_parse_error:
            return _tool_error(f"参数不是合法 JSON：{decision.arguments_parse_error}"), True
        tool = self.tools.get(original_name)
        if tool is None:
            return _tool_error(f"未知工具 {original_name}；可用工具见 tools/list"), True
        schema = tool.get("inputSchema") or {"type": "object"}
        try:
            jsonschema.validate(decision.arguments, schema)
        except jsonschema.ValidationError as exc:
            return _tool_error(f"参数不满足 inputSchema: {exc.message}"), True
        try:
            return self.executor(original_name, decision.arguments), False
        except Exception as exc:  # 执行器异常作为工具错误回填，不中断循环
            return _tool_error(f"工具执行异常: {exc}"), False

    @staticmethod
    def _assistant_message(response: Any) -> dict[str, Any]:
        return {
            "role": "assistant",
            "content": response.content,
            "tool_calls": [
                {
                    "id": d.call_id,
                    "type": "function",
                    "function": {
                        "name": d.name,
                        "arguments": json.dumps(d.arguments, ensure_ascii=False),
                    },
                }
                for d in response.tool_calls
            ],
        }

    def _finish(
        self,
        base: dict[str, Any],
        call_log: list[dict[str, Any]],
        final_answer: str | None,
        stopped_reason: str,
        validation_errors: int,
        usage: dict[str, Any] | None,
        *,
        execution_status: str = "completed",
        error_category: str | None = None,
        error_detail: str | None = None,
    ) -> EvalRecord:
        response_raw: dict[str, Any] = {
            "tool_calls": call_log,
            "final_answer": final_answer,
            "rounds": len(call_log),
            "stopped_reason": stopped_reason,
            "validation_errors": validation_errors,
        }
        if usage:
            response_raw["usage"] = usage
        if error_detail:
            response_raw["error_detail"] = error_detail[:500]
        return EvalRecord(
            **base,
            response_raw=response_raw,
            execution_status=execution_status,
            error_category=error_category,
        )


def _tool_error(message: str) -> dict[str, Any]:
    """MCP 风格的工具执行错误（isError），供模型自我纠正。"""
    return {"content": [{"type": "text", "text": message}], "isError": True}
