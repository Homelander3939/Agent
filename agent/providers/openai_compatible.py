"""OpenAI-compatible chat-completions provider.

Both Ollama (``/v1/chat/completions``) and LM Studio expose an
OpenAI-compatible REST API, as does the real OpenAI API and many other
self-hosted servers (vLLM, text-generation-webui, LocalAI, etc.). Using
plain ``requests`` instead of the official ``openai`` SDK keeps the
dependency footprint small and avoids SDK version coupling.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import requests

from agent.config import ProviderConfig
from agent.providers.base import BaseProvider, ChatMessage, LLMResponse, ProviderError


class OpenAICompatibleProvider(BaseProvider):
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.name = config.name

    def chat(
        self,
        messages: List[ChatMessage],
        *,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
    ) -> LLMResponse:
        url = self.config.base_url.rstrip("/") + "/chat/completions"
        api_key = self.config.resolve_api_key() or "not-needed"

        payload: Dict[str, Any] = {
            "model": self.config.model,
            "messages": [m.to_openai_dict() for m in messages],
            "temperature": temperature,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        headers = {
            "Authorization": "Bearer " + api_key,
            "Content-Type": "application/json",
        }

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=self.config.timeout)
        except requests.RequestException as exc:
            raise ProviderError(f"[{self.name}] request failed: {exc}") from exc

        if resp.status_code >= 400:
            raise ProviderError(f"[{self.name}] HTTP {resp.status_code}: {resp.text[:500]}")

        data = resp.json()
        try:
            choice = data["choices"][0]["message"]
        except (KeyError, IndexError) as exc:
            raise ProviderError(f"[{self.name}] unexpected response shape: {data}") from exc

        content = choice.get("content") or ""
        tool_calls = choice.get("tool_calls") or []

        return LLMResponse(
            content=content,
            provider=self.name,
            model=self.config.model,
            tool_calls=tool_calls,
            raw=data,
        )
