import textwrap

import requests
from fastapi.testclient import TestClient

from agent.providers.base import ChatMessage, LLMResponse
from agent.server import create_app


def _make_client(tmp_path, monkeypatch):
    monkeypatch.delenv("AGENT_CONFIG", raising=False)
    monkeypatch.chdir(tmp_path)
    app = create_app()
    return TestClient(app)


def test_index_serves_html(tmp_path, monkeypatch):
    client = _make_client(tmp_path, monkeypatch)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Local Agent Framework" in resp.text
    assert "settingsBtn" in resp.text


def test_chat_returns_provider_error_message_when_unreachable(tmp_path, monkeypatch):
    client = _make_client(tmp_path, monkeypatch)

    def fake_post(*a, **kw):
        raise requests.ConnectionError("nope")

    monkeypatch.setattr(requests, "post", fake_post)
    resp = client.post("/api/chat", json={"prompt": "hello"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["error"] is True
    assert "No model provider is currently reachable" in data["final_answer"]


def test_chat_success_returns_final_answer(tmp_path, monkeypatch):
    client = _make_client(tmp_path, monkeypatch)

    def fake_chat(self, messages, *, tools=None, temperature=None):
        return LLMResponse(content="hi there", provider="ollama", model="qwen2.5:32b-instruct")

    from agent.providers.router import ProviderRouter

    monkeypatch.setattr(ProviderRouter, "chat", fake_chat)
    resp = client.post("/api/chat", json={"prompt": "hello"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["error"] is False
    assert data["final_answer"] == "hi there"


def test_list_providers_reports_ollama_enabled_by_default(tmp_path, monkeypatch):
    client = _make_client(tmp_path, monkeypatch)
    resp = client.get("/api/providers")
    assert resp.status_code == 200
    providers = resp.json()["providers"]
    names = {p["name"]: p for p in providers}
    assert names["ollama"]["enabled"] is True
    assert names["ollama"]["active"] is True
    assert names["lmstudio"]["enabled"] is False
    assert names["ollama"]["is_local"] is True


def test_discover_endpoint_reports_scanned_servers(tmp_path, monkeypatch):
    client = _make_client(tmp_path, monkeypatch)

    class FakeResponse:
        def __init__(self, json_data):
            self._json_data = json_data

        def raise_for_status(self):
            pass

        def json(self):
            return self._json_data

    def fake_get(url, timeout):
        if "api/tags" in url:
            return FakeResponse({"models": [{"name": "qwen2.5:32b-instruct"}]})
        raise requests.ConnectionError("not running")

    monkeypatch.setattr(requests, "get", fake_get)
    resp = client.get("/api/discover")
    assert resp.status_code == 200
    servers = {s["name"]: s for s in resp.json()["servers"]}
    assert servers["ollama"]["reachable"] is True
    assert servers["ollama"]["models"] == ["qwen2.5:32b-instruct"]
    assert servers["lmstudio"]["reachable"] is False


def test_configure_provider_updates_and_persists(tmp_path, monkeypatch):
    client = _make_client(tmp_path, monkeypatch)
    resp = client.post(
        "/api/providers/lmstudio",
        json={"base_url": "http://localhost:1234/v1", "model": "local-model", "enabled": True, "exclusive": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["provider"]["enabled"] is True
    providers = {p["name"]: p for p in data["providers"]}
    assert providers["lmstudio"]["active"] is True
    assert providers["ollama"]["enabled"] is False, "exclusive select should disable other providers"

    # Persisted to config.yaml so a fresh load reflects the change.
    cfg_path = tmp_path / "config.yaml"
    assert cfg_path.exists()
    saved = cfg_path.read_text()
    assert "lmstudio" in saved


def test_configure_custom_provider_adds_new_entry(tmp_path, monkeypatch):
    client = _make_client(tmp_path, monkeypatch)
    resp = client.post(
        "/api/providers/myserver",
        json={"base_url": "http://localhost:9000/v1", "model": "custom-model", "enabled": True, "exclusive": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    names = [p["name"] for p in data["providers"]]
    assert "myserver" in names
    myserver = next(p for p in data["providers"] if p["name"] == "myserver")
    assert myserver["base_url"] == "http://localhost:9000/v1"
    assert myserver["active"] is True


def test_configure_provider_rejects_disabling_all_providers(tmp_path, monkeypatch):
    client = _make_client(tmp_path, monkeypatch)
    resp = client.post("/api/providers/ollama", json={"enabled": False})
    assert resp.status_code == 400
    # State must be rolled back, not left half-applied.
    providers = client.get("/api/providers").json()["providers"]
    ollama = next(p for p in providers if p["name"] == "ollama")
    assert ollama["enabled"] is True


def test_chat_clear_resets_history(tmp_path, monkeypatch):
    client = _make_client(tmp_path, monkeypatch)

    def fake_chat(self, messages, *, tools=None, temperature=None):
        return LLMResponse(content="hi", provider="ollama", model="m")

    from agent.providers.router import ProviderRouter

    monkeypatch.setattr(ProviderRouter, "chat", fake_chat)
    client.post("/api/chat", json={"prompt": "hello"})
    resp = client.post("/api/chat/clear")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
