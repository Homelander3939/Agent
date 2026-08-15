from agent.core.agent_loop import AgentLoop
from agent.providers.base import LLMResponse
from agent.tools.base import Tool, ToolRegistry, ToolResult


class FakeRouter:
    """Replays a scripted sequence of LLMResponse objects, one per .chat() call."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = 0

    def chat(self, messages, tools=None, temperature=None):
        response = self._responses[self.calls]
        self.calls += 1
        return response


def make_echo_tool():
    def handler(text: str) -> ToolResult:
        return ToolResult(ok=True, output=f"echo:{text}")

    return Tool(
        name="echo",
        description="Echo text back",
        parameters={"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
        handler=handler,
    )


def test_agent_loop_returns_final_answer_without_tool_calls():
    router = FakeRouter([LLMResponse(content="all done", provider="fake", model="m")])
    registry = ToolRegistry()
    loop = AgentLoop(router=router, tools=registry, workspace=".", max_steps=5)
    result = loop.run("do nothing")
    assert result.final_answer == "all done"
    assert router.calls == 1


def test_agent_loop_executes_structured_tool_call_then_final_answer():
    registry = ToolRegistry()
    registry.register(make_echo_tool())

    tool_call_response = LLMResponse(
        content="",
        provider="fake",
        model="m",
        tool_calls=[
            {"id": "1", "function": {"name": "echo", "arguments": '{"text": "hi"}'}}
        ],
    )
    final_response = LLMResponse(content="the tool said echo:hi", provider="fake", model="m")

    router = FakeRouter([tool_call_response, final_response])
    loop = AgentLoop(router=router, tools=registry, workspace=".", max_steps=5)
    result = loop.run("please echo hi")

    assert result.final_answer == "the tool said echo:hi"
    tool_steps = [s for s in result.steps if s.role == "tool"]
    assert len(tool_steps) == 1
    assert tool_steps[0].content == "echo:hi"


def test_agent_loop_parses_text_fallback_tool_call():
    registry = ToolRegistry()
    registry.register(make_echo_tool())

    text_call_response = LLMResponse(
        content='```tool_call\n{"name": "echo", "arguments": {"text": "fallback"}}\n```',
        provider="fake",
        model="m",
    )
    final_response = LLMResponse(content="done via fallback", provider="fake", model="m")

    router = FakeRouter([text_call_response, final_response])
    loop = AgentLoop(router=router, tools=registry, workspace=".", max_steps=5)
    result = loop.run("please echo fallback")

    assert result.final_answer == "done via fallback"


def test_agent_loop_stops_at_max_steps():
    tool_call_response = LLMResponse(
        content="",
        provider="fake",
        model="m",
        tool_calls=[{"id": "1", "function": {"name": "echo", "arguments": '{"text": "loop"}'}}],
    )
    registry = ToolRegistry()
    registry.register(make_echo_tool())
    router = FakeRouter([tool_call_response] * 10)
    loop = AgentLoop(router=router, tools=registry, workspace=".", max_steps=3)
    result = loop.run("loop forever")
    assert result.stopped_reason == "max_steps"
    assert router.calls == 3
