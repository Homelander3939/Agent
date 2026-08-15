"""Sandboxed-ish Python execution skill for quick calculations/data munging.

Runs in a fresh subprocess (not the agent's own process) so a runaway or
malicious snippet can't touch the framework's memory/state directly, and
is bound by a timeout like the shell tool.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List

from agent.tools.base import Tool, ToolResult


def build_python_tools(workspace: str) -> List[Tool]:
    def run_python(code: str, timeout: int = 30) -> ToolResult:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, dir=workspace, encoding="utf-8"
        ) as tmp:
            tmp.write(code)
            tmp_path = Path(tmp.name)
        try:
            proc = subprocess.run(
                [sys.executable, str(tmp_path)],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=workspace,
            )
        except subprocess.TimeoutExpired:
            return ToolResult(ok=False, output=f"Python execution timed out after {timeout}s")
        finally:
            tmp_path.unlink(missing_ok=True)

        output = proc.stdout
        if proc.stderr:
            output += ("\n" if output else "") + f"[stderr]\n{proc.stderr}"
        return ToolResult(ok=proc.returncode == 0, output=output.strip() or "(no output)")

    return [
        Tool(
            name="run_python",
            description="Execute a Python snippet in a subprocess and return stdout/stderr.",
            parameters={
                "type": "object",
                "properties": {
                    "code": {"type": "string"},
                    "timeout": {"type": "integer"},
                },
                "required": ["code"],
            },
            handler=run_python,
        )
    ]
