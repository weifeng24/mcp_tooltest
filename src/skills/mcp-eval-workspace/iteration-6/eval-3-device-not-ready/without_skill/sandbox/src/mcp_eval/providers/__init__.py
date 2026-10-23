"""模型提供方工厂：按配置创建 provider。"""
from __future__ import annotations

from typing import Any

from .base import ProviderError
from .openai_compat import OpenAICompatProvider

DEFAULT_BASE_URLS = {
    "deepseek": "https://api.deepseek.com",
    "kimi": "https://api.moonshot.cn/v1",
    "openrouter": "https://openrouter.ai/api/v1",
}


def create_provider(model_config: dict[str, Any]) -> OpenAICompatProvider:
    provider = model_config["provider"]
    if provider not in DEFAULT_BASE_URLS:
        raise ProviderError(f"未知 provider: {provider}")
    generation = model_config.get("generation", {})
    return OpenAICompatProvider(
        model=model_config["model"],
        base_url=model_config.get("base_url") or DEFAULT_BASE_URLS[provider],
        api_key_env=model_config["api_key_env"],
        temperature=generation.get("temperature", 0.0),
        max_tokens=generation.get("max_tokens", 1024),
    )
