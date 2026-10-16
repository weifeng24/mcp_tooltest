"""OpenAI 兼容接口的模型提供方实现。

DeepSeek、Kimi（Moonshot）、OpenRouter 均提供 OpenAI 兼容的
chat/completions 端点与 tool calling，差异仅在 base_url/模型名/密钥，
因此共用一个实现，由配置区分。

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
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
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
            with urllib.request.urlopen(request, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:500]
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
        decisions = []
        for call in message.get("tool_calls") or []:
            function = call.get("function", {})
            raw_args = function.get("arguments", "{}")
            parse_error = None
            try:
                arguments = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args)
            except (json.JSONDecodeError, TypeError) as exc:
                arguments = {}
                parse_error = f"arguments JSON 解析失败: {exc}"
            decisions.append(
                ToolCallDecision(
                    call_id=str(call.get("id", "")),
                    name=str(function.get("name", "")),
                    arguments=arguments,
                    arguments_parse_error=parse_error,
                )
            )
        return ProviderResponse(
            content=message.get("content"),
            tool_calls=decisions,
            usage=data.get("usage"),
            raw=data,
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
