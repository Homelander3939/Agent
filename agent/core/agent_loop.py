"""The agent's step loop: send messages, execute any requested tool calls,
feed results back, repeat until the model produces a final answer or the
step budget runs out.

Supports two tool-calling styles simultaneously so it works well with both
capable cloud models and smaller local (27B-32B) open models:

1. **Native OpenAI-style tool calls** -- passed via the ``tools=`` schema
   and returned as structured ``tool_calls`` on the response. Ollama/LM
   Studio support this for compatible models.
2. **Text fallback** -- if a model doesn't (reliably) emit structured tool
   calls, it can instead reply with a fenced block::

       ```tool_call
       {"name": "read_file", "arguments": {"path": "README.md"}}
       ```

   which is parsed out of the plain content.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional

from agent.providers.base import ChatMessage, LLMResponse
from agent.providers.router import ProviderRouter
from agent.tools.base import ToolRegistry, parse_tool_arguments

logger = logging.getLogger(__name__)

TOOL_CALL_BLOCK_RE = re.compile(r"```tool_call\s*(\{.*?\})\s*```", re.DOTALL)

SYSTEM_PROMPT_TEMPLATE = """You are a local-first autonomous coding & browsing agent, similar in \
spirit to Codex/Claude Code (and to hosted "build me an app" tools like Lovable), running entirely \
on the user's own machine. You have access to tools for reading/writing files, running shell \
commands, executing Python, browsing the web with a real Chromium browser, searching the web, and \
keeping notes/todos.

You are expected to be able to deliver fully functional, runnable outputs, not just descriptions:
- When asked to build a web app or other digital product, actually scaffold it (e.g. via \
`run_shell` with `npm create vite@latest`, `npx create-next-app`, or plain HTML/CSS/JS files via \
`write_file`), install dependencies, write real working code, and verify it runs/builds before \
declaring the task done.
- You are connected to the internet: use `web_search`/`web_fetch` to look up current library docs, \
APIs, and examples, and to find and download real assets (images, icons, fonts, sample data) the \
project needs -- don't invent fake placeholder URLs. Use the browser tools when a site needs JS \
rendering or interaction that a plain fetch can't handle.
- You can improve yourself: this agent's own source code is just files in a workspace like any \
other, so if asked to modify or extend the agent's own behavior, read the relevant files under \
`agent/` and edit them the same way you would any other project, then run the test suite to check \
you haven't broken anything.

Workspace root: {workspace}

Available tools:
{tool_manifest}

Rules:
- Always prefer using a tool over guessing when you need information about the filesystem, the web, \
or need to run code.
- Break multi-step tasks into a todo list with todo_add/todo_complete so progress survives many steps.
- When you are confident you have finished the user's request, reply with a normal final answer and \
do not call any more tools.
- If a tool call fails, read the error and adjust your next call rather than repeating the same call.
- If your provider doesn't support structured tool calling, you may instead respond with a fenced \
block exactly like:
```tool_call
{{"name": "<tool_name>", "arguments": {{...}}}}
```
"""


@dataclass
class StepRecord:
    role: str
    content: str
    tool_name: Optional[str] = None


@dataclass
class AgentLoopResult:
    final_answer: str
    steps: List[StepRecord] = field(default_factory=list)
    stopped_reason: str = "final_answer"


def _extract_text_tool_call(content: str):
    match = TOOL_CALL_BLOCK_RE.search(content)
    if not match:
        return None
    try:
        payload = json.loads(match.group(1))
        return payload.get("name"), payload.get("arguments", {})
    except json.JSONDecodeError:
        return None


class AgentLoop:
    def __init__(
        self,
        router: ProviderRouter,
        tools: ToolRegistry,
        workspace: str,
        max_steps: int = 25,
    ):
        self.router = router
        self.tools = tools
        self.workspace = workspace
        self.max_steps = max_steps

    def _system_message(self) -> ChatMessage:
        return ChatMessage(
            role="system",
            content=SYSTEM_PROMPT_TEMPLATE.format(
                workspace=self.workspace,
                tool_manifest=self.tools.render_text_manifest(),
            ),
        )

    def run(self, user_prompt: str, history: Optional[List[ChatMessage]] = None) -> AgentLoopResult:
        messages: List[ChatMessage] = [self._system_message()]
        if history:
            messages.extend(history)
        messages.append(ChatMessage(role="user", content=user_prompt))

        steps: List[StepRecord] = [StepRecord(role="user", content=user_prompt)]
        schemas = self.tools.openai_schemas()

        for step_index in range(self.max_steps):
            response: LLMResponse = self.router.chat(messages, tools=schemas)

            tool_calls = response.tool_calls
            text_call = None
            if not tool_calls and response.content:
                text_call = _extract_text_tool_call(response.content)

            if not tool_calls and not text_call:
                steps.append(StepRecord(role="assistant", content=response.content))
                return AgentLoopResult(final_answer=response.content, steps=steps)

            messages.append(ChatMessage(role="assistant", content=response.content, tool_calls=tool_calls or None))
            steps.append(StepRecord(role="assistant", content=response.content or "(tool call)"))

            if tool_calls:
                for call in tool_calls:
                    fn = call.get("function", call)
                    name = fn.get("name")
                    arguments = parse_tool_arguments(fn.get("arguments"))
                    result = self.tools.dispatch(name, arguments)
                    steps.append(StepRecord(role="tool", content=result.to_text(), tool_name=name))
                    messages.append(
                        ChatMessage(
                            role="tool",
                            content=result.to_text(),
                            tool_call_id=call.get("id", name),
                            name=name,
                        )
                    )
            elif text_call:
                name, arguments = text_call
                result = self.tools.dispatch(name, arguments)
                steps.append(StepRecord(role="tool", content=result.to_text(), tool_name=name))
                messages.append(
                    ChatMessage(role="user", content=f"[tool result for {name}]\n{result.to_text()}")
                )

        return AgentLoopResult(
            final_answer="(stopped: reached max_steps without a final answer)",
            steps=steps,
            stopped_reason="max_steps",
        )
