"""Base classes for the agent's tool ("skill") system.

A ``Tool`` is a single callable capability the agent can invoke: reading a
file, running a shell command, driving the browser, etc. Tools describe
themselves with a JSON-Schema ``parameters`` block so they can be exposed
to models that support native OpenAI-style function/tool calling, while
also being invokable through the plain-text ReAct-style fallback used for
local models that don't reliably emit structured tool calls.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ToolResult:
    ok: bool
    output: str
    data: Optional[Dict[str, Any]] = None

    def to_text(self) -> str:
        return self.output


@dataclass
class Tool:
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable[..., ToolResult]

    def to_openai_schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def run(self, **kwargs: Any) -> ToolResult:
        try:
            return self.handler(**kwargs)
        except Exception as exc:  # noqa: BLE001 - tool failures must not crash the agent
            return ToolResult(ok=False, output=f"Tool '{self.name}' raised an error: {exc}")


class ToolRegistry:
    """Holds every skill available to the agent for the current session."""

    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def all(self) -> List[Tool]:
        return list(self._tools.values())

    def openai_schemas(self) -> List[Dict[str, Any]]:
        return [t.to_openai_schema() for t in self._tools.values()]

    def render_text_manifest(self) -> str:
        """Human/LLM-readable listing used by the plain-text ReAct fallback
        prompt for models without native tool-calling support."""
        lines = []
        for tool in self._tools.values():
            props = tool.parameters.get("properties", {})
            arg_hint = ", ".join(f'"{k}": <{v.get("type", "any")}>' for k, v in props.items())
            lines.append(f"- {tool.name}({arg_hint}): {tool.description}")
        return "\n".join(lines)

    def dispatch(self, name: str, arguments: Dict[str, Any]) -> ToolResult:
        tool = self.get(name)
        if tool is None:
            return ToolResult(ok=False, output=f"Unknown tool '{name}'. Available: {list(self._tools)}")
        return tool.run(**arguments)


def parse_tool_arguments(raw: Any) -> Dict[str, Any]:
    """Best-effort parsing of tool-call arguments, which providers may hand
    back as a JSON string (OpenAI style) or already-parsed dict."""
    if isinstance(raw, dict):
        return raw
    if raw in (None, ""):
        return {}
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {}
