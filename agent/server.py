"""Minimal local web UI: a single-page chat interface served over
localhost, so the portable Windows build can just be double-clicked and
opens a browser tab -- no separate desktop UI toolkit required.
"""
from __future__ import annotations

import threading
import webbrowser
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from agent.config import load_config
from agent.core.session import AgentSession
from agent.providers.base import ProviderError

INDEX_HTML = """<!DOCTYPE html>
<html lang=\"en\">
<head>
<meta charset=\"utf-8\" />
<title>Local Agent</title>
<style>
  body { font-family: system-ui, sans-serif; max-width: 860px; margin: 2rem auto; background:#0f1115; color:#e6e6e6; }
  #log { border: 1px solid #333; border-radius: 8px; padding: 1rem; min-height: 50vh; overflow-y: auto; white-space: pre-wrap; background:#171923;}
  .msg-user { color: #8ab4f8; margin: 0.5rem 0; }
  .msg-agent { color: #a5d6a7; margin: 0.5rem 0; }
  .msg-tool { color: #888; font-size: 0.85em; }
  form { display: flex; gap: 0.5rem; margin-top: 1rem; }
  input { flex: 1; padding: 0.6rem; border-radius: 6px; border: 1px solid #333; background:#171923; color:#eee; }
  button { padding: 0.6rem 1.2rem; border-radius: 6px; border: none; background: #4c8bf5; color: white; cursor: pointer; }
</style>
</head>
<body>
  <h2>🤖 Local Agent Framework</h2>
  <div id=\"log\"></div>
  <form id=\"f\">
    <input id=\"prompt\" autocomplete=\"off\" placeholder=\"Ask the agent to do something...\" />
    <button type=\"submit\">Send</button>
  </form>
<script>
const log = document.getElementById('log');
const form = document.getElementById('f');
const input = document.getElementById('prompt');
function append(cls, text) {
  const div = document.createElement('div');
  div.className = cls;
  div.textContent = text;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}
form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const prompt = input.value.trim();
  if (!prompt) return;
  append('msg-user', 'you: ' + prompt);
  input.value = '';
  append('msg-tool', 'thinking...');
  const resp = await fetch('/api/chat', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({prompt})
  });
  const data = await resp.json();
  log.lastChild.remove();
  for (const step of data.steps) {
    if (step.role === 'tool') append('msg-tool', '  -> ' + step.tool_name + ': ' + step.content.slice(0, 300));
  }
  append('msg-agent', 'agent: ' + data.final_answer);
});
</script>
</body>
</html>
"""


class ChatRequest(BaseModel):
    prompt: str


def create_app(config_path: Optional[str] = None) -> FastAPI:
    app = FastAPI(title="Local Agent Framework")
    config = load_config(config_path)
    session = AgentSession(config)

    @app.on_event("shutdown")
    def _shutdown():
        session.close()

    @app.get("/", response_class=HTMLResponse)
    def index():
        return INDEX_HTML

    @app.post("/api/chat")
    def chat(req: ChatRequest):
        try:
            result = session.ask(req.prompt)
        except ProviderError as exc:
            return {"final_answer": f"No provider available: {exc}", "steps": []}
        return {
            "final_answer": result.final_answer,
            "steps": [
                {"role": s.role, "content": s.content, "tool_name": s.tool_name} for s in result.steps
            ],
        }

    return app


def serve(host: str = "127.0.0.1", port: int = 8765, config_path: Optional[str] = None) -> None:
    import uvicorn

    app = create_app(config_path)
    url = f"http://{host}:{port}"
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    print(f"Local Agent Framework running at {url}")
    uvicorn.run(app, host=host, port=port)
