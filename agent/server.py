"""Minimal local web UI: a single-page chat interface served over
localhost, so the portable Windows build can just be double-clicked and
opens a browser tab -- no separate desktop UI toolkit required.

Besides the chat endpoint, this also exposes a small settings API so the
UI can *discover* local model servers (Ollama, LM Studio, and other
OpenAI-compatible local runtimes) and let the user pick one from a list
instead of hand-editing YAML.
"""
from __future__ import annotations

import logging
import threading
import webbrowser
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from agent.config import load_config
from agent.core.session import AgentSession
from agent.providers.base import ProviderError
from agent.providers.discovery import discover_local_servers
from agent.web_ui import INDEX_HTML

logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    prompt: str


class ProviderUpdateRequest(BaseModel):
    base_url: Optional[str] = None
    model: Optional[str] = None
    enabled: Optional[bool] = None
    api_key: Optional[str] = None
    provider_type: str = "openai_compatible"
    exclusive: bool = False


def _provider_summary(config, active_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return provider info safe to send to the browser -- never the
    resolved value of a real secret, only whether one is configured."""
    summary = []
    for p in config.providers:
        summary.append(
            {
                "name": p.name,
                "type": p.type,
                "base_url": p.base_url,
                "model": p.model,
                "enabled": p.enabled,
                "timeout": p.timeout,
                "is_local": "localhost" in p.base_url or "127.0.0.1" in p.base_url,
                "has_api_key_env": bool(p.api_key_env),
                "active": active_name == p.name,
            }
        )
    return summary


def create_app(config_path: Optional[str] = None) -> FastAPI:
    config = load_config(config_path)
    session = AgentSession(config, config_path=config_path)
    lock = threading.Lock()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        session.close()

    app = FastAPI(title="Local Agent Framework", lifespan=lifespan)

    @app.get("/", response_class=HTMLResponse)
    def index():
        # Explicitly disable caching so browsers always fetch the latest UI
        # instead of silently reusing a stale copy from a previous build
        # (a common source of "why don't I see my changes?" confusion).
        return HTMLResponse(
            content=INDEX_HTML,
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate",
                "Pragma": "no-cache",
            },
        )

    @app.post("/api/chat")
    def chat(req: ChatRequest):
        try:
            with lock:
                result = session.ask(req.prompt)
        except ProviderError as exc:
            logger.warning("Provider error while handling chat request: %s", exc)
            return {
                "final_answer": (
                    "No model provider is currently reachable. Check that your local "
                    "Ollama/LM Studio server is running (or that a cloud API key is "
                    "configured), then try again. Open Settings to scan for local "
                    "servers."
                ),
                "steps": [],
                "error": True,
            }
        return {
            "final_answer": result.final_answer,
            "steps": [
                {"role": s.role, "content": s.content, "tool_name": s.tool_name} for s in result.steps
            ],
            "error": False,
        }

    @app.post("/api/chat/clear")
    def clear_chat():
        with lock:
            session.history = []
        return {"ok": True}

    @app.get("/api/providers")
    def list_providers():
        with lock:
            enabled = session.config.enabled_providers()
            active_name = enabled[0].name if enabled else None
            return {"providers": _provider_summary(session.config, active_name)}

    @app.get("/api/discover")
    def discover():
        """Scan localhost for running Ollama/LM Studio/OpenAI-compatible
        servers and report what models each one currently has available."""
        servers = discover_local_servers()
        return {"servers": [s.to_dict() for s in servers]}

    @app.post("/api/providers/{name}")
    def configure_provider(name: str, req: ProviderUpdateRequest):
        with lock:
            try:
                provider = session.configure_provider(
                    name,
                    base_url=req.base_url,
                    model=req.model,
                    enabled=req.enabled,
                    api_key=req.api_key,
                    provider_type=req.provider_type,
                    exclusive=req.exclusive,
                )
            except ProviderError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            enabled = session.config.enabled_providers()
            active_name = enabled[0].name if enabled else None
            return {
                "provider": {
                    "name": provider.name,
                    "type": provider.type,
                    "base_url": provider.base_url,
                    "model": provider.model,
                    "enabled": provider.enabled,
                },
                "providers": _provider_summary(session.config, active_name),
            }

    return app


def serve(host: str = "127.0.0.1", port: int = 8765, config_path: Optional[str] = None) -> None:
    import uvicorn

    app = create_app(config_path)
    url = f"http://{host}:{port}"
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    print(f"Local Agent Framework running at {url}")
    uvicorn.run(app, host=host, port=port)
