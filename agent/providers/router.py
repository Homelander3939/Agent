"""Router that tries local models first, then falls back to cloud models.

This is the core of the "local-first, cloud-secondary" requirement: the
router iterates over the *enabled* providers in the order they appear in
the config (local providers are listed first by default) and only moves
on to the next provider if the current one raises a :class:`ProviderError`
(connection refused because Ollama/LM Studio isn't running, timeout,
malformed response, etc).
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from agent.config import Config, ProviderConfig
from agent.providers.base import BaseProvider, ChatMessage, LLMResponse, ProviderError

logger = logging.getLogger(__name__)


def _build_provider(config: ProviderConfig) -> BaseProvider:
    if config.type == "openai_compatible":
        from agent.providers.openai_compatible import OpenAICompatibleProvider

        return OpenAICompatibleProvider(config)
    if config.type == "anthropic":
        from agent.providers.anthropic import AnthropicProvider

        return AnthropicProvider(config)
    raise ValueError(f"Unknown provider type: {config.type!r}")


class ProviderRouter:
    def __init__(self, config: Config):
        self.config = config
        self.providers: List[BaseProvider] = [
            _build_provider(p) for p in config.enabled_providers()
        ]
        if not self.providers:
            raise ProviderError(
                "No providers are enabled. Enable at least one in config.yaml "
                "(by default this should be your local Ollama/LM Studio server)."
            )

    def chat(
        self,
        messages: List[ChatMessage],
        *,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
    ) -> LLMResponse:
        errors = []
        temp = self.config.agent.temperature if temperature is None else temperature
        for provider in self.providers:
            try:
                logger.info("Trying provider %s (model=%s)", provider.name, provider.config.model)
                return provider.chat(messages, tools=tools, temperature=temp)
            except ProviderError as exc:
                logger.warning("Provider %s failed: %s", provider.name, exc)
                errors.append(str(exc))
                continue
        raise ProviderError(
            "All configured providers failed:\n" + "\n".join(errors)
        )
