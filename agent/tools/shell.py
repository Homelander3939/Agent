"""Shell command execution skill.

Runs commands through the system shell with a timeout and captures both
stdout and stderr. This is deliberately not sandboxed beyond a working
directory + timeout: the framework runs entirely on the user's own
machine under their own OS permissions, exactly like Codex CLI's
"auto" execution mode.
"""
from __future__ import annotations

import subprocess
from typing import List

from agent.tools.base import Tool, ToolResult
from agent.tools.filesystem import WorkspaceGuard


def build_shell_tools(workspace: str) -> List[Tool]:
    guard = WorkspaceGuard(workspace)

    def run_shell(command: str, timeout: int = 60, cwd: str = ".") -> ToolResult:
        work_dir = guard.resolve(cwd)
        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=str(work_dir),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return ToolResult(ok=False, output=f"Command timed out after {timeout}s: {command}")
        output = proc.stdout
        if proc.stderr:
            output += ("\n" if output else "") + f"[stderr]\n{proc.stderr}"
        output += f"\n[exit code: {proc.returncode}]"
        return ToolResult(ok=proc.returncode == 0, output=output.strip())

    return [
        Tool(
            name="run_shell",
            description=(
                "Execute a shell command on the local machine inside the workspace "
                "and return stdout/stderr/exit code. Use for builds, tests, git, "
                "package installs, etc."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "timeout": {"type": "integer", "description": "Seconds before killing the process"},
                    "cwd": {"type": "string", "description": "Working directory relative to workspace"},
                },
                "required": ["command"],
            },
            handler=run_shell,
        )
    ]
