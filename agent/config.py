"""Configuration loading for the local-agent framework.

Configuration is resolved, in increasing priority order, from:

1. Built-in defaults (local-first: LM Studio on ``http://localhost:1234``).
2. A YAML config file (``config.yaml`` in the current directory, or the
   path given by the ``AGENT_CONFIG`` environment variable).
3. Environment variables / a ``.env`` file (highest priority), so API keys
   never need to be committed to disk in plain YAML.

The design goal is "it just works" for someone who only has Ollama or LM
Studio running locally, while still allowing an optional cloud model to be
configured as a fallback for when local models struggle with a task.
"""
from __future__ import annotations

import copy
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from dotenv import load_dotenv

DEFAULT_CONFIG: Dict[str, Any] = {
    # Ordered list of providers. The agent tries them in order and only
    # falls through to the next one if a call fails (connection refused,
    # timeout, HTTP error) -- i.e. local models are ALWAYS tried first.
    "providers": [
        {
            "name": "lmstudio",
            "type": "openai_compatible",
            "base_url": "http://localhost:1234/v1",
            "api_key": "lm-studio",
            # LM Studio's local server usually needs no key at all, but recent
            # versions let you require one (Settings -> Local Server -> "API
            # key"). Set LMSTUDIO_API_KEY in .env to supply it; falls back to
            # the placeholder "lm-studio" value above when unset.
            "api_key_env": "LMSTUDIO_API_KEY",
            "model": "local-model",
            "enabled": True,
            "timeout": 120,
        },
        {
            "name": "ollama",
            "type": "openai_compatible",
            "base_url": "http://localhost:11434/v1",
            "api_key": "ollama",  # Ollama ignores the key but the SDK/HTTP shape requires one.
            "model": "qwen2.5:32b-instruct",
            "enabled": False,
            "timeout": 120,
        },
        {
            "name": "openai",
            "type": "openai_compatible",
            "base_url": "https://api.openai.com/v1",
            "api_key_env": "OPENAI_API_KEY",
            "model": "gpt-4o-mini",
            "enabled": False,
            "timeout": 120,
        },
        {
            "name": "anthropic",
            "type": "anthropic",
            "base_url": "https://api.anthropic.com",
            "api_key_env": "ANTHROPIC_API_KEY",
            "model": "claude-3-5-sonnet-latest",
            "enabled": False,
            "timeout": 120,
        },
    ],
    "agent": {
        "max_steps": 25,
        "temperature": 0.2,
        "workspace": ".",
        "history_limit": 40,
    },
    "browser": {
        "headless": True,
        "download_dir": "./agent_downloads",
    },
    "memory": {
        "path": "./.agent_memory.json",
    },
}


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key == "providers" and isinstance(value, list):
            # Providers are merged by name so a user config can override a
            # single provider (e.g. flip lmstudio.enabled=true) without
            # having to restate every field.
            merged_by_name = {p["name"]: copy.deepcopy(p) for p in result.get("providers", [])}
            for prov in value:
                name = prov.get("name")
                if name in merged_by_name:
                    merged_by_name[name].update(prov)
                else:
                    merged_by_name[name] = prov
            result["providers"] = list(merged_by_name.values())
        elif isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


@dataclass
class ProviderConfig:
    name: str
    type: str
    base_url: str
    model: str
    api_key: Optional[str] = None
    api_key_env: Optional[str] = None
    enabled: bool = True
    timeout: int = 120

    def resolve_api_key(self) -> Optional[str]:
        if self.api_key_env:
            env_value = os.environ.get(self.api_key_env)
            if env_value:
                return env_value
        return self.api_key


@dataclass
class AgentSettings:
    max_steps: int = 25
    temperature: float = 0.2
    workspace: str = "."
    history_limit: int = 40


@dataclass
class BrowserSettings:
    headless: bool = True
    download_dir: str = "./agent_downloads"


@dataclass
class MemorySettings:
    path: str = "./.agent_memory.json"


@dataclass
class Config:
    providers: List[ProviderConfig] = field(default_factory=list)
    agent: AgentSettings = field(default_factory=AgentSettings)
    browser: BrowserSettings = field(default_factory=BrowserSettings)
    memory: MemorySettings = field(default_factory=MemorySettings)

    def enabled_providers(self) -> List[ProviderConfig]:
        """Local-first ordering: providers keep the order declared in the
        config file, which by default puts Ollama/LM Studio ahead of any
        cloud provider. Only providers explicitly enabled are returned."""
        return [p for p in self.providers if p.enabled]


def _find_default_config_path() -> Optional[Path]:
    env_path = os.environ.get("AGENT_CONFIG")
    if env_path:
        return Path(env_path)
    candidate = Path.cwd() / "config.yaml"
    if candidate.exists():
        return candidate
    return None


def load_config(path: Optional[str] = None) -> Config:
    """Load configuration, merging defaults, YAML file, and environment."""
    load_dotenv(override=False)

    merged = copy.deepcopy(DEFAULT_CONFIG)

    config_path = Path(path) if path else _find_default_config_path()
    if config_path and config_path.exists():
        with open(config_path, "r", encoding="utf-8") as fh:
            user_cfg = yaml.safe_load(fh) or {}
        merged = _deep_merge(merged, user_cfg)

    providers = [ProviderConfig(**p) for p in merged["providers"]]
    agent_settings = AgentSettings(**merged["agent"])
    browser_settings = BrowserSettings(**merged["browser"])
    memory_settings = MemorySettings(**merged["memory"])

    return Config(
        providers=providers,
        agent=agent_settings,
        browser=browser_settings,
        memory=memory_settings,
    )


def default_save_path() -> Path:
    """Where settings changes made from the UI get persisted to, so a
    provider chosen via the settings panel is still selected next launch."""
    env_path = os.environ.get("AGENT_CONFIG")
    if env_path:
        return Path(env_path)
    return Path.cwd() / "config.yaml"


def config_to_dict(config: Config) -> Dict[str, Any]:
    """Serialize a :class:`Config` back into a plain dict suitable for
    ``yaml.safe_dump``. Only the placeholder/non-secret ``api_key`` field is
    ever written to disk -- real secrets should stay in ``api_key_env`` /
    ``.env``, which is untouched by this round-trip."""
    return {
        "providers": [
            {
                "name": p.name,
                "type": p.type,
                "base_url": p.base_url,
                "model": p.model,
                "api_key": p.api_key,
                "api_key_env": p.api_key_env,
                "enabled": p.enabled,
                "timeout": p.timeout,
            }
            for p in config.providers
        ],
        "agent": {
            "max_steps": config.agent.max_steps,
            "temperature": config.agent.temperature,
            "workspace": config.agent.workspace,
            "history_limit": config.agent.history_limit,
        },
        "browser": {
            "headless": config.browser.headless,
            "download_dir": config.browser.download_dir,
        },
        "memory": {
            "path": config.memory.path,
        },
    }


def save_config(config: Config, path: Optional[str] = None) -> Path:
    """Persist ``config`` to a YAML file so changes made through the web UI's
    settings panel (which provider/model is active) survive a restart."""
    target = Path(path) if path else default_save_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8") as fh:
        yaml.safe_dump(config_to_dict(config), fh, sort_keys=False)
    return target
