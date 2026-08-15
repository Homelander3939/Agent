from agent.cli import _handle_command
from agent.config import load_config
from agent.core.session import AgentSession


def _make_session(tmp_path, monkeypatch):
    monkeypatch.delenv("AGENT_CONFIG", raising=False)
    monkeypatch.chdir(tmp_path)
    config = load_config()
    return AgentSession(config)


def test_handle_command_ignores_plain_prompts(tmp_path, monkeypatch):
    session = _make_session(tmp_path, monkeypatch)
    try:
        assert _handle_command(session, "list the files here") is False
    finally:
        session.close()


def test_help_and_providers_commands_are_recognized(tmp_path, monkeypatch):
    session = _make_session(tmp_path, monkeypatch)
    try:
        assert _handle_command(session, "/help") is True
        assert _handle_command(session, "/providers") is True
    finally:
        session.close()


def test_use_command_switches_active_provider_exclusively(tmp_path, monkeypatch):
    session = _make_session(tmp_path, monkeypatch)
    try:
        assert session.config.providers[0].name == "lmstudio"
        assert _handle_command(session, "/use ollama") is True
        ollama = next(p for p in session.config.providers if p.name == "ollama")
        lmstudio = next(p for p in session.config.providers if p.name == "lmstudio")
        assert ollama.enabled is True
        assert lmstudio.enabled is False
    finally:
        session.close()


def test_set_command_updates_base_url_and_model(tmp_path, monkeypatch):
    session = _make_session(tmp_path, monkeypatch)
    try:
        assert _handle_command(
            session, "/set lmstudio base_url=http://localhost:1234/v1 model=my-model"
        ) is True
        lmstudio = next(p for p in session.config.providers if p.name == "lmstudio")
        assert lmstudio.base_url == "http://localhost:1234/v1"
        assert lmstudio.model == "my-model"
    finally:
        session.close()


def test_unknown_slash_command_is_not_recognized(tmp_path, monkeypatch):
    session = _make_session(tmp_path, monkeypatch)
    try:
        assert _handle_command(session, "/nope") is False
    finally:
        session.close()
