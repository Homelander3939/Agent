"""Wires configuration, providers, and tools together into a runnable
agent session -- the object the CLI and web UI both drive.
"""
from __future__ import annotations

from typing import List, Optional

from agent.config import Config, load_config
from agent.core.agent_loop import AgentLoop, AgentLoopResult
from agent.providers.base import ChatMessage
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
    def __init__(self, config: Optional[Config] = None):
        self.config = config or load_config()
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

    def close(self) -> None:
        if self.browser_session is not None:
            self.browser_session.close()

    def __enter__(self) -> "AgentSession":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
