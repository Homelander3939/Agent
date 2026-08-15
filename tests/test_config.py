import os
import textwrap

import pytest

from agent.config import load_config


def test_default_config_is_local_first(tmp_path, monkeypatch):
    monkeypatch.delenv("AGENT_CONFIG", raising=False)
    monkeypatch.chdir(tmp_path)
    config = load_config()
    enabled = config.enabled_providers()
    assert len(enabled) == 1
    assert enabled[0].name == "ollama"
    assert enabled[0].base_url == "http://localhost:11434/v1"


def test_yaml_override_can_enable_cloud_fallback(tmp_path):
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(
        textwrap.dedent(
            """
            providers:
              - name: ollama
                model: llama3.1:8b
              - name: openai
                enabled: true
            agent:
              workspace: /tmp
            """
        )
    )
    config = load_config(str(cfg_path))
    names = [p.name for p in config.enabled_providers()]
    assert names == ["ollama", "openai"], "local provider must stay first"
    ollama = next(p for p in config.providers if p.name == "ollama")
    assert ollama.model == "llama3.1:8b"
    assert config.agent.workspace == "/tmp"


def test_api_key_env_resolution(monkeypatch, tmp_path):
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(
        textwrap.dedent(
            """
            providers:
              - name: openai
                enabled: true
            """
        )
    )
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")
    config = load_config(str(cfg_path))
    openai_cfg = next(p for p in config.providers if p.name == "openai")
    assert openai_cfg.resolve_api_key() == "test-key-123"
