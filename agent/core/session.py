"""Wires configuration, providers, and tools together into a runnable
agent session -- the object the CLI and web UI both drive.
"""
from __future__ import annotations

import copy
from typing import List, Optional

from agent.config import Config, ProviderConfig, load_config, save_config
from agent.core.agent_loop import AgentLoop, AgentLoopResult
from agent.providers.base import ChatMessage, ProviderError
from agent.providers.router import ProviderRouter
from agent.tools.base import ToolRegistry
from agent.tools.browser import BrowserSession, build_browser_tools
from agent.tools.filesystem import build_filesystem_tools
from agent.tools.memory import build_memory_tools
from agent.tools.python_exec import build_python_tools
from agent.tools.shell import build_shell_tools
from agent.tools.todo import build_todo_tools
from agent.tools.web import build_web_tools


class AgentSession:
    def __init__(self, config: Optional[Config] = None, config_path: Optional[str] = None):
        self.config = config or load_config(config_path)
        self.config_path = config_path
        self.registry = ToolRegistry()
        self.browser_session: Optional[BrowserSession] = None
        self._register_tools()
        self.router = ProviderRouter(self.config)
        self.loop = AgentLoop(
            router=self.router,
            tools=self.registry,
            workspace=self.config.agent.workspace,
            max_steps=self.config.agent.max_steps,
        )
        self.history: List[ChatMessage] = []

    def _register_tools(self) -> None:
        workspace = self.config.agent.workspace
        for tool in build_filesystem_tools(workspace):
            self.registry.register(tool)
        for tool in build_shell_tools(workspace):
            self.registry.register(tool)
        for tool in build_python_tools(workspace):
            self.registry.register(tool)
        for tool in build_web_tools():
            self.registry.register(tool)
        for tool in build_memory_tools(self.config.memory.path):
            self.registry.register(tool)
        for tool in build_todo_tools():
            self.registry.register(tool)

        browser_tools, browser_session = build_browser_tools(
            headless=self.config.browser.headless,
            download_dir=self.config.browser.download_dir,
        )
        self.browser_session = browser_session
        for tool in browser_tools:
            self.registry.register(tool)

    def ask(self, prompt: str) -> AgentLoopResult:
        result = self.loop.run(prompt, history=self.history)
        self.history.append(ChatMessage(role="user", content=prompt))
        self.history.append(ChatMessage(role="assistant", content=result.final_answer))
        self.history = self.history[-self.config.agent.history_limit :]
        return result

    def configure_provider(
        self,
        name: str,
        *,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        enabled: Optional[bool] = None,
        api_key: Optional[str] = None,
        provider_type: str = "openai_compatible",
        exclusive: bool = False,
    ) -> ProviderConfig:
        """Add or update a provider entry (used by the settings panel to
        wire up a locally-discovered server), rebuild the router so the
        change takes effect immediately, and persist it to disk.

        If ``exclusive`` is true, every other provider is disabled first so
        the chosen local model is the only one tried -- handy for "just use
        this one" from the discovery/scan UI.

        Raises :class:`ProviderError` (and leaves the configuration
        untouched) if applying the update would leave zero providers
        enabled, so a bad request can never brick a running session.
        """
        previous_providers = copy.deepcopy(self.config.providers)
        previous_router = self.router

        existing = next((p for p in self.config.providers if p.name == name), None)
        if exclusive:
            for p in self.config.providers:
                if p is not existing:
                    p.enabled = False

        if existing is None:
            existing = ProviderConfig(
                name=name,
                type=provider_type,
                base_url=base_url or "",
                model=model or "",
                api_key=api_key,
                enabled=enabled if enabled is not None else True,
            )
            # New custom local providers go to the front so they're tried
            # before any pre-existing cloud fallback (local-first ordering).
            self.config.providers.insert(0, existing)
        else:
            if base_url is not None:
                existing.base_url = base_url
            if model is not None:
                existing.model = model
            if api_key is not None:
                existing.api_key = api_key
            existing.enabled = enabled if enabled is not None else (True if exclusive else existing.enabled)

        try:
            self.rebuild_router()
        except ProviderError:
            self.config.providers = previous_providers
            self.router = previous_router
            self.loop.router = previous_router
            raise
        self.persist_config()
        return existing

    def rebuild_router(self) -> None:
        self.router = ProviderRouter(self.config)
        self.loop.router = self.router

    def persist_config(self) -> None:
        save_config(self.config, self.config_path)

    def close(self) -> None:
        if self.browser_session is not None:
            self.browser_session.close()

    def __enter__(self) -> "AgentSession":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
