import pytest
import requests

from agent.config import ProviderConfig
from agent.providers.base import ChatMessage, ProviderError
from agent.providers.openai_compatible import OpenAICompatibleProvider
from agent.providers.router import ProviderRouter
from agent.config import Config, AgentSettings, BrowserSettings, MemorySettings


class FakeResponse:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text

    def json(self):
        return self._json_data


def test_openai_compatible_success(monkeypatch):
    config = ProviderConfig(
        name="ollama", type="openai_compatible", base_url="http://localhost:11434/v1",
        model="qwen2.5:32b-instruct", api_key="ollama",
    )
    provider = OpenAICompatibleProvider(config)

    def fake_post(url, json, headers, timeout):
        assert url == "http://localhost:11434/v1/chat/completions"
        assert headers["Authorization"] == "Bearer " + "ollama"
        return FakeResponse(json_data={"choices": [{"message": {"content": "hello world"}}]})

    monkeypatch.setattr(requests, "post", fake_post)
    result = provider.chat([ChatMessage(role="user", content="hi")])
    assert result.content == "hello world"
    assert result.provider == "ollama"


def test_openai_compatible_http_error_raises_provider_error(monkeypatch):
    config = ProviderConfig(
        name="ollama", type="openai_compatible", base_url="http://localhost:11434/v1",
        model="m", api_key="ollama",
    )
    provider = OpenAICompatibleProvider(config)

    def fake_post(url, json, headers, timeout):
        return FakeResponse(status_code=500, text="boom")

    monkeypatch.setattr(requests, "post", fake_post)
    with pytest.raises(ProviderError):
        provider.chat([ChatMessage(role="user", content="hi")])


def test_openai_compatible_connection_error_raises_provider_error(monkeypatch):
    config = ProviderConfig(
        name="ollama", type="openai_compatible", base_url="http://localhost:11434/v1",
        model="m", api_key="ollama",
    )
    provider = OpenAICompatibleProvider(config)

    def fake_post(*a, **kw):
        raise requests.ConnectionError("connection refused")

    monkeypatch.setattr(requests, "post", fake_post)
    with pytest.raises(ProviderError):
        provider.chat([ChatMessage(role="user", content="hi")])


def test_router_falls_back_to_next_provider_on_failure(monkeypatch):
    local_cfg = ProviderConfig(
        name="ollama", type="openai_compatible", base_url="http://localhost:11434/v1",
        model="m", api_key="ollama", enabled=True,
    )
    cloud_cfg = ProviderConfig(
        name="openai", type="openai_compatible", base_url="https://api.openai.com/v1",
        model="gpt-4o-mini", api_key="k", enabled=True,
    )
    config = Config(
        providers=[local_cfg, cloud_cfg],
        agent=AgentSettings(),
        browser=BrowserSettings(),
        memory=MemorySettings(),
    )
    router = ProviderRouter(config)

    call_log = []

    def fake_post(url, json, headers, timeout):
        call_log.append(url)
        if "localhost" in url:
            raise requests.ConnectionError("ollama not running")
        return FakeResponse(json_data={"choices": [{"message": {"content": "cloud answer"}}]})

    monkeypatch.setattr(requests, "post", fake_post)
    result = router.chat([ChatMessage(role="user", content="hi")])
    assert result.content == "cloud answer"
    assert result.provider == "openai"
    assert len(call_log) == 2, "must try local provider first, then fall back"


def test_router_raises_when_all_providers_fail(monkeypatch):
    local_cfg = ProviderConfig(
        name="ollama", type="openai_compatible", base_url="http://localhost:11434/v1",
        model="m", api_key="ollama", enabled=True,
    )
    config = Config(
        providers=[local_cfg], agent=AgentSettings(), browser=BrowserSettings(), memory=MemorySettings(),
    )
    router = ProviderRouter(config)

    def fake_post(*a, **kw):
        raise requests.ConnectionError("nope")

    monkeypatch.setattr(requests, "post", fake_post)
    with pytest.raises(ProviderError):
        router.chat([ChatMessage(role="user", content="hi")])
