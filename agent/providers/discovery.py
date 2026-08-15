"""Local model server discovery.

The whole point of this framework is "download it, run it, and it talks to
whatever local model server you already have open" -- so instead of making
the user hand-edit YAML to find out whether Ollama/LM Studio are running and
what model name to type, this module actively probes the well-known local
ports for those servers (and other OpenAI-compatible local runtimes such as
LM Studio, vLLM, text-generation-webui, and LocalAI) and reports back what
it finds, including the list of models each one currently has loaded/pulled.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import requests

# (name, base_url, kind) for the servers we know how to talk to out of the
# box. ``kind`` selects which probe function to use for that server's API
# shape. Local-first: these are all localhost endpoints.
KNOWN_LOCAL_SERVERS: List[Dict[str, str]] = [
    {"name": "ollama", "base_url": "http://localhost:11434", "kind": "ollama"},
    {"name": "lmstudio", "base_url": "http://localhost:1234/v1", "kind": "openai_compatible"},
    # Other common local OpenAI-compatible runtimes, offered as "custom" so
    # a match here doesn't overwrite the built-in ollama/lmstudio entries.
    {"name": "text-generation-webui", "base_url": "http://localhost:5000/v1", "kind": "openai_compatible"},
    {"name": "vllm", "base_url": "http://localhost:8000/v1", "kind": "openai_compatible"},
    {"name": "localai", "base_url": "http://localhost:8080/v1", "kind": "openai_compatible"},
]

DEFAULT_PROBE_TIMEOUT = 1.5


@dataclass
class DiscoveredServer:
    name: str
    base_url: str
    kind: str
    reachable: bool
    models: List[str] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "base_url": self.base_url,
            "kind": self.kind,
            "reachable": self.reachable,
            "models": self.models,
            "error": self.error,
        }


def probe_ollama(base_url: str, timeout: float = DEFAULT_PROBE_TIMEOUT) -> DiscoveredServer:
    """Probe an Ollama server via its native ``/api/tags`` endpoint, which
    lists every model the user has pulled (independent of what's currently
    loaded into memory)."""
    url = base_url.rstrip("/") + "/api/tags"
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        models = [m.get("name") for m in data.get("models", []) if m.get("name")]
        return DiscoveredServer(name="ollama", base_url=base_url, kind="ollama", reachable=True, models=models)
    except requests.RequestException as exc:
        return DiscoveredServer(name="ollama", base_url=base_url, kind="ollama", reachable=False, error=str(exc))
    except (ValueError, KeyError, TypeError) as exc:
        return DiscoveredServer(
            name="ollama", base_url=base_url, kind="ollama", reachable=True, error=f"unexpected response: {exc}"
        )


def probe_openai_compatible(
    name: str, base_url: str, timeout: float = DEFAULT_PROBE_TIMEOUT
) -> DiscoveredServer:
    """Probe an OpenAI-compatible ``/v1/models`` endpoint (LM Studio, vLLM,
    text-generation-webui, LocalAI, and many other self-hosted runtimes all
    implement this)."""
    url = base_url.rstrip("/") + "/models"
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        models = [m.get("id") for m in data.get("data", []) if m.get("id")]
        return DiscoveredServer(
            name=name, base_url=base_url, kind="openai_compatible", reachable=True, models=models
        )
    except requests.RequestException as exc:
        return DiscoveredServer(
            name=name, base_url=base_url, kind="openai_compatible", reachable=False, error=str(exc)
        )
    except (ValueError, KeyError, TypeError) as exc:
        return DiscoveredServer(
            name=name,
            base_url=base_url,
            kind="openai_compatible",
            reachable=True,
            error=f"unexpected response: {exc}",
        )


def probe_server(server: Dict[str, str], timeout: float = DEFAULT_PROBE_TIMEOUT) -> DiscoveredServer:
    if server["kind"] == "ollama":
        return probe_ollama(server["base_url"], timeout=timeout)
    return probe_openai_compatible(server["name"], server["base_url"], timeout=timeout)


def discover_local_servers(
    servers: Optional[List[Dict[str, str]]] = None, timeout: float = DEFAULT_PROBE_TIMEOUT
) -> List[DiscoveredServer]:
    """Probe every known local server address and return the results.

    Unreachable servers are still included (with ``reachable=False``) so the
    UI can show what was tried, not just what succeeded.
    """
    candidates = servers if servers is not None else KNOWN_LOCAL_SERVERS
    return [probe_server(server, timeout=timeout) for server in candidates]
