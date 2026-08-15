"""Task/todo tracking skill: lets the agent plan multi-step work and check
items off, which keeps smaller local models on track over long tasks by
giving them an explicit, re-displayed checklist instead of relying on
long-context recall.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import List


@dataclass
class TodoList:
    items: List[dict] = field(default_factory=list)
    _counter: itertools.count = field(default_factory=lambda: itertools.count(1))

    def add(self, text: str) -> int:
        item_id = next(self._counter)
        self.items.append({"id": item_id, "text": text, "done": False})
        return item_id

    def complete(self, item_id: int) -> bool:
        for item in self.items:
            if item["id"] == item_id:
                item["done"] = True
                return True
        return False

    def render(self) -> str:
        if not self.items:
            return "(no todos yet)"
        lines = []
        for item in self.items:
            mark = "x" if item["done"] else " "
            lines.append(f"[{mark}] #{item['id']} {item['text']}")
        return "\n".join(lines)


from agent.tools.base import Tool, ToolResult  # noqa: E402  (avoid circular import at module load)


def build_todo_tools() -> List[Tool]:
    todos = TodoList()

    def todo_add(text: str) -> ToolResult:
        item_id = todos.add(text)
        return ToolResult(ok=True, output=f"Added todo #{item_id}: {text}")

    def todo_complete(id: int) -> ToolResult:
        ok = todos.complete(id)
        return ToolResult(ok=ok, output=f"Marked #{id} done" if ok else f"No todo with id {id}")

    def todo_list() -> ToolResult:
        return ToolResult(ok=True, output=todos.render())

    return [
        Tool(
            name="todo_add",
            description="Add a new task to the running plan/checklist.",
            parameters={"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
            handler=todo_add,
        ),
        Tool(
            name="todo_complete",
            description="Mark a task on the checklist as done by its numeric id.",
            parameters={"type": "object", "properties": {"id": {"type": "integer"}}, "required": ["id"]},
            handler=todo_complete,
        ),
        Tool(
            name="todo_list",
            description="Show the current checklist of tasks and their completion state.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=todo_list,
        ),
    ]
