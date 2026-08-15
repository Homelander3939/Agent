"""Persistent memory skill: a simple key/value + note store on disk.

This lets the agent remember facts across steps within a session and,
because it's just a JSON file, across separate runs of the CLI too --
similar in spirit to Codex/Claude "memory" files, without needing a
database server.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List

from agent.tools.base import Tool, ToolResult


class MemoryStore:
    def __init__(self, path: str):
        self.path = Path(path)
        if self.path.exists():
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
        else:
            self.data = {}

    def save(self):
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    def set(self, key: str, value: str):
        self.data[key] = value
        self.save()

    def get(self, key: str) -> str:
        return self.data.get(key, "")

    def all(self) -> dict:
        return self.data


def build_memory_tools(path: str) -> List[Tool]:
    store = MemoryStore(path)

    def memory_set(key: str, value: str) -> ToolResult:
        store.set(key, value)
        return ToolResult(ok=True, output=f"Remembered '{key}'")

    def memory_get(key: str) -> ToolResult:
        value = store.get(key)
        return ToolResult(ok=True, output=value or f"No memory stored for '{key}'")

    def memory_list() -> ToolResult:
        if not store.all():
            return ToolResult(ok=True, output="(memory is empty)")
        return ToolResult(ok=True, output="\n".join(f"{k}: {v}" for k, v in store.all().items()))

    return [
        Tool(
            name="memory_set",
            description="Persist a fact as a key/value pair for later recall in this or future sessions.",
            parameters={
                "type": "object",
                "properties": {"key": {"type": "string"}, "value": {"type": "string"}},
                "required": ["key", "value"],
            },
            handler=memory_set,
        ),
        Tool(
            name="memory_get",
            description="Recall a previously stored fact by key.",
            parameters={"type": "object", "properties": {"key": {"type": "string"}}, "required": ["key"]},
            handler=memory_get,
        ),
        Tool(
            name="memory_list",
            description="List all stored memory key/value pairs.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=memory_list,
        ),
    ]
