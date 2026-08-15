"""Minimal Anthropic Messages API adapter (secondary/cloud fallback only)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import requests

from agent.config import ProviderConfig
from agent.providers.base import BaseProvider, ChatMessage, LLMResponse, ProviderError


class AnthropicProvider(BaseProvider):
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
        api_key = self.config.resolve_api_key()
        if not api_key:
            raise ProviderError(f"[{self.name}] no API key configured (set {self.config.api_key_env})")

        system_parts = [m.content for m in messages if m.role == "system"]
        conversation = [m for m in messages if m.role != "system"]

        def _to_anthropic_message(m: ChatMessage) -> Dict[str, Any]:
            if m.role == "tool":
                return {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": m.tool_call_id or m.name or "unknown",
                            "content": m.content,
                        }
                    ],
                }
            return {"role": m.role, "content": m.content}

        url = self.config.base_url.rstrip("/") + "/v1/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload: Dict[str, Any] = {
            "model": self.config.model,
            "max_tokens": 4096,
            "temperature": temperature,
            "system": "\n".join(system_parts) if system_parts else None,
            "messages": [_to_anthropic_message(m) for m in conversation],
        }
        if tools:
            payload["tools"] = tools

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=self.config.timeout)
        except requests.RequestException as exc:
            raise ProviderError(f"[{self.name}] request failed: {exc}") from exc

        if resp.status_code >= 400:
            raise ProviderError(f"[{self.name}] HTTP {resp.status_code}: {resp.text[:500]}")

        data = resp.json()
        content_blocks = data.get("content", [])
        text = "".join(b.get("text", "") for b in content_blocks if b.get("type") == "text")
        tool_calls = [b for b in content_blocks if b.get("type") == "tool_use"]

        return LLMResponse(
            content=text,
            provider=self.name,
            model=self.config.model,
            tool_calls=tool_calls,
            raw=data,
        )
