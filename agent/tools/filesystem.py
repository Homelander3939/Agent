"""Filesystem skills: read, write, list, search, and patch local files.

All paths are resolved relative to (and confined within) the configured
workspace directory so the agent cannot wander outside the project folder
it was launched against.
"""
from __future__ import annotations

import difflib
import os
from pathlib import Path
from typing import Any, Dict

from agent.tools.base import Tool, ToolResult


class WorkspaceGuard:
    def __init__(self, root: str):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def resolve(self, relative_path: str) -> Path:
        candidate = (self.root / relative_path).resolve()
        if self.root not in candidate.parents and candidate != self.root:
            raise PermissionError(
                f"Path '{relative_path}' escapes the workspace root '{self.root}'"
            )
        return candidate


def build_filesystem_tools(workspace: str) -> list[Tool]:
    guard = WorkspaceGuard(workspace)

    def read_file(path: str, start_line: int = 1, end_line: int = -1) -> ToolResult:
        target = guard.resolve(path)
        if not target.exists():
            return ToolResult(ok=False, output=f"File not found: {path}")
        text = target.read_text(encoding="utf-8", errors="replace").splitlines()
        end = len(text) if end_line == -1 else end_line
        snippet = text[max(start_line - 1, 0):end]
        numbered = "\n".join(f"{i + start_line}: {line}" for i, line in enumerate(snippet))
        return ToolResult(ok=True, output=numbered or "(empty file)")

    def write_file(path: str, content: str, overwrite: bool = True) -> ToolResult:
        target = guard.resolve(path)
        if target.exists() and not overwrite:
            return ToolResult(ok=False, output=f"File already exists: {path} (set overwrite=true)")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return ToolResult(ok=True, output=f"Wrote {len(content)} bytes to {path}")

    def edit_file(path: str, old_text: str, new_text: str) -> ToolResult:
        target = guard.resolve(path)
        if not target.exists():
            return ToolResult(ok=False, output=f"File not found: {path}")
        original = target.read_text(encoding="utf-8", errors="replace")
        if old_text not in original:
            return ToolResult(ok=False, output="old_text not found verbatim in file; no changes made")
        if original.count(old_text) > 1:
            return ToolResult(
                ok=False,
                output="old_text matches multiple locations; include more context to make it unique",
            )
        updated = original.replace(old_text, new_text, 1)
        target.write_text(updated, encoding="utf-8")
        diff = "\n".join(
            difflib.unified_diff(
                original.splitlines(), updated.splitlines(), fromfile=path, tofile=path, lineterm=""
            )
        )
        return ToolResult(ok=True, output=f"Edited {path}\n{diff}")

    def list_dir(path: str = ".") -> ToolResult:
        target = guard.resolve(path)
        if not target.exists():
            return ToolResult(ok=False, output=f"Path not found: {path}")
        entries = []
        for entry in sorted(target.iterdir()):
            kind = "dir" if entry.is_dir() else "file"
            entries.append(f"{kind}\t{entry.name}")
        return ToolResult(ok=True, output="\n".join(entries) or "(empty directory)")

    def search_files(query: str, glob: str = "**/*", max_results: int = 50) -> ToolResult:
        matches = []
        for entry in guard.root.glob(glob):
            if entry.is_dir():
                continue
            try:
                text = entry.read_text(encoding="utf-8", errors="ignore")
            except (UnicodeDecodeError, OSError):
                continue
            if query in text:
                rel = entry.relative_to(guard.root)
                for lineno, line in enumerate(text.splitlines(), start=1):
                    if query in line:
                        matches.append(f"{rel}:{lineno}: {line.strip()}")
                        if len(matches) >= max_results:
                            return ToolResult(ok=True, output="\n".join(matches))
        return ToolResult(ok=True, output="\n".join(matches) or "No matches found")

    return [
        Tool(
            name="read_file",
            description="Read a text file from the workspace (optionally a line range).",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path relative to workspace root"},
                    "start_line": {"type": "integer", "description": "1-indexed start line"},
                    "end_line": {"type": "integer", "description": "1-indexed end line, -1 = end of file"},
                },
                "required": ["path"],
            },
            handler=read_file,
        ),
        Tool(
            name="write_file",
            description="Create a file or overwrite it entirely with new content.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                    "overwrite": {"type": "boolean"},
                },
                "required": ["path", "content"],
            },
            handler=write_file,
        ),
        Tool(
            name="edit_file",
            description="Replace one exact, unique occurrence of old_text with new_text in a file.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old_text": {"type": "string"},
                    "new_text": {"type": "string"},
                },
                "required": ["path", "old_text", "new_text"],
            },
            handler=edit_file,
        ),
        Tool(
            name="list_dir",
            description="List files and directories at a given path in the workspace.",
            parameters={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": [],
            },
            handler=list_dir,
        ),
        Tool(
            name="search_files",
            description="Search workspace files for a literal text query, returning matching lines.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "glob": {"type": "string", "description": "Glob pattern, default '**/*'"},
                    "max_results": {"type": "integer"},
                },
                "required": ["query"],
            },
            handler=search_files,
        ),
    ]
