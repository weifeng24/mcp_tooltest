"""模型提供方抽象：统一的对话请求/响应结构。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class ProviderError(RuntimeError):
    """模型 API 调用失败（网络、鉴权、响应格式等）。"""


@dataclass
class ToolCallDecision:
    """模型作出的一次工具调用决策。"""

    call_id: str
    name: str
    arguments: dict[str, Any]
    arguments_parse_error: str | None = None
    arguments_raw: str | None = None


@dataclass
class ProviderResponse:
    """一次对话响应：要么含工具调用决策，要么含最终文本。"""

    content: str | None = None
    tool_calls: list[ToolCallDecision] = field(default_factory=list)
    usage: dict[str, Any] | None = None
    raw: dict[str, Any] | None = None
    finish_reason: str | None = None
