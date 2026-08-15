import requests

from agent.providers.discovery import (
    DiscoveredServer,
    discover_local_servers,
    probe_ollama,
    probe_openai_compatible,
)


class FakeResponse:
    def __init__(self, status_code=200, json_data=None):
        self.status_code = status_code
        self._json_data = json_data or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"status {self.status_code}")

    def json(self):
        return self._json_data


def test_probe_ollama_success(monkeypatch):
    def fake_get(url, timeout):
        assert url == "http://localhost:11434/api/tags"
        return FakeResponse(json_data={"models": [{"name": "qwen2.5:32b-instruct"}, {"name": "llama3.1:8b"}]})

    monkeypatch.setattr(requests, "get", fake_get)
    result = probe_ollama("http://localhost:11434")
    assert result.reachable is True
    assert result.models == ["qwen2.5:32b-instruct", "llama3.1:8b"]
    assert result.name == "ollama"


def test_probe_ollama_unreachable(monkeypatch):
    def fake_get(url, timeout):
        raise requests.ConnectionError("connection refused")

    monkeypatch.setattr(requests, "get", fake_get)
    result = probe_ollama("http://localhost:11434")
    assert result.reachable is False
    assert "connection refused" in result.error


def test_probe_openai_compatible_success(monkeypatch):
    def fake_get(url, timeout):
        assert url == "http://localhost:1234/v1/models"
        return FakeResponse(json_data={"data": [{"id": "local-model"}]})

    monkeypatch.setattr(requests, "get", fake_get)
    result = probe_openai_compatible("lmstudio", "http://localhost:1234/v1")
    assert result.reachable is True
    assert result.models == ["local-model"]


def test_probe_openai_compatible_unreachable(monkeypatch):
    def fake_get(url, timeout):
        raise requests.ConnectionError("nope")

    monkeypatch.setattr(requests, "get", fake_get)
    result = probe_openai_compatible("lmstudio", "http://localhost:1234/v1")
    assert result.reachable is False


def test_discover_local_servers_uses_correct_probe_per_kind(monkeypatch):
    def fake_get(url, timeout):
        if "api/tags" in url:
            return FakeResponse(json_data={"models": [{"name": "m1"}]})
        return FakeResponse(json_data={"data": [{"id": "m2"}]})

    monkeypatch.setattr(requests, "get", fake_get)
    servers = discover_local_servers(
        servers=[
            {"name": "ollama", "base_url": "http://localhost:11434", "kind": "ollama"},
            {"name": "lmstudio", "base_url": "http://localhost:1234/v1", "kind": "openai_compatible"},
        ]
    )
    assert len(servers) == 2
    by_name = {s.name: s for s in servers}
    assert by_name["ollama"].models == ["m1"]
    assert by_name["lmstudio"].models == ["m2"]
    assert all(isinstance(s, DiscoveredServer) for s in servers)


def test_discovered_server_to_dict():
    server = DiscoveredServer(name="ollama", base_url="http://localhost:11434", kind="ollama", reachable=True, models=["m1"])
    d = server.to_dict()
    assert d == {
        "name": "ollama",
        "base_url": "http://localhost:11434",
        "kind": "ollama",
        "reachable": True,
        "models": ["m1"],
        "error": None,
    }
