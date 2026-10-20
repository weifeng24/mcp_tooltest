"""OpenAI 兼容接口的模型提供方实现。

只适用于已核实的 chat/completions 协议。不同产品/套餐的端点、
模型和工具调用行为需独立验证；Kimi Coding Plan 不能仅凭 API key
形式认定与通用 Moonshot API 等价。

仅依赖标准库 urllib，避免引入额外依赖。密钥只从环境变量读取。
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from .base import ProviderError, ProviderResponse, ToolCallDecision


class OpenAICompatProvider:
    source = "api"
    def __init__(
        self,
        *,
        model: str,
        base_url: str,
        api_key_env: str,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        timeout: int = 60,
    ) -> None:
        key = os.environ.get(api_key_env)
        if not key:
            raise ProviderError(
                f"环境变量 {api_key_env} 未设置；请先在 shell 中 export 后再运行"
            )
        self._key = key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

    def chat(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]], *, timeout: float | None = None
    ) -> ProviderResponse:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            budget = min(self.timeout, timeout) if timeout is not None else self.timeout
            if budget <= 0:
                raise ProviderError("请求时间预算已耗尽")
            with urllib.request.urlopen(request, timeout=budget) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace").replace(self._key, "[REDACTED]")[:500]
            raise ProviderError(f"HTTP {exc.code}: {body}") from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ProviderError(f"请求失败: {exc}") from exc
        return self._parse(data)

    @staticmethod
    def _parse(data: dict[str, Any]) -> ProviderResponse:
        try:
            message = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"响应缺少 choices[0].message: {str(data)[:300]}") from exc
        if not isinstance(message, dict) or message.get("content") is not None and not isinstance(message["content"], str):
            raise ProviderError("响应 message/content 格式错误")
        calls = message.get("tool_calls")
        if calls is None:
            calls = []
        if not isinstance(calls, list):
            raise ProviderError("响应 tool_calls 必须为数组")
        decisions = []
        ids = set()
        for call in calls:
            if not isinstance(call, dict) or not isinstance(call.get("function"), dict):
                raise ProviderError("响应工具决策缺少 function")
            function = call.get("function", {})
            if (not isinstance(call.get("id"), str) or not call["id"] or call["id"] in ids
                    or not isinstance(function.get("name"), str) or not function["name"]):
                raise ProviderError("工具调用 id/name 缺失或 id 重复")
            ids.add(call["id"])
            raw_args = function.get("arguments", "{}")
            parse_error = None
            try:
                arguments = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                if not isinstance(arguments, dict):
                    raise ValueError("arguments 必须为 JSON 对象")
            except (ValueError, TypeError) as exc:
                arguments = {}
                parse_error = f"arguments JSON 解析失败: {exc}"
            decisions.append(
                ToolCallDecision(
                    call_id=str(call.get("id", "")),
                    name=str(function.get("name", "")),
                    arguments=arguments,
                    arguments_parse_error=parse_error,
                    arguments_raw=raw_args if isinstance(raw_args, str) else json.dumps(raw_args),
                )
            )
        return ProviderResponse(
            content=message.get("content"),
            tool_calls=decisions,
            usage=data.get("usage"),
            raw=data,
            finish_reason=data["choices"][0].get("finish_reason"),
        )

    @staticmethod
    def mcp_tools_to_openai(
        tools: list[dict[str, Any]], name_map: dict[str, str] | None = None
    ) -> list[dict[str, Any]]:
        """MCP tools/list 的工具定义 → OpenAI tools 格式。

        name_map: 原始工具名 → API 安全名（可选；API 限制 ^[a-zA-Z0-9_-]{1,64}$，
        含点号等字符的 MCP 名必须映射后下发）。
        """
        name_map = name_map or {}
        return [
            {
                "type": "function",
                "function": {
                    "name": name_map.get(t["name"], t["name"]),
                    "description": t.get("description", ""),
                    "parameters": t.get("inputSchema", {"type": "object", "properties": {}}),
                },
            }
            for t in tools
        ]
