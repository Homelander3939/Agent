# Local Agent Framework

A **local-first agentic framework**: an autonomous coding & browsing agent
(in the spirit of Codex CLI / Claude Code) that talks primarily to models
you run yourself with **Ollama** or **LM Studio**, with optional cloud API
keys (OpenAI, Anthropic) as a secondary fallback. It ships with a built-in
**Chromium browser** the agent can drive, plus filesystem, shell, Python,
web-search, memory, and todo-list skills — all runnable on Windows, macOS,
or Linux, with a portable, double-click Windows build available via CI.

> **Honesty note:** the "built-in browser" automates a real Chromium via
> [Playwright](https://playwright.dev/) rather than reimplementing a
> browser rendering engine from scratch (which would be a multi-million
> line effort on its own). This is the same approach used by every
> "computer use"/browsing agent in the wild — the agent layer is what we
> built; Chromium itself is the open-source engine we drive.

## Features

- **Local-first, cloud-secondary** provider routing: providers are tried in
  the order configured (Ollama/LM Studio first); a cloud provider is only
  contacted if every enabled local provider fails or is disabled.
- **Works with or without native tool-calling.** The agent loop understands
  both OpenAI-style structured `tool_calls` (supported by Ollama/LM Studio
  for compatible models) and a plain-text fenced fallback, so 27B-32B class
  open models that don't reliably emit structured calls still work.
- **Built-in skills:** file read/write/edit/search, shell execution, Python
  execution, a real Chromium browser (navigate/click/type/read/screenshot/
  run JS), web search + fetch (no API key required), persistent memory, and
  a todo/checklist tool to keep long multi-step tasks on track.
- **Two ways to use it:** an interactive CLI (`local-agent`) or a minimal
  local web chat UI (`local-agent --serve`) that opens in your browser.
- **Portable Windows build:** a PyInstaller-based packaging script + GitHub
  Actions workflow produce a single folder you unzip and run via
  `Start-Agent.bat` — no Python install required on the target machine.

## Quick start (from source)

```bash
pip install -e .
playwright install chromium      # one-time download of the browser binary
cp config/config.example.yaml config.yaml
cp .env.example .env              # only needed if you enable a cloud provider
```

1. Install [Ollama](https://ollama.com) and pull a model, e.g.:
   ```bash
   ollama pull qwen2.5:32b-instruct
   ```
   (Other good local choices in the 27B-32B range: `gemma2:27b`,
   `command-r:35b`; smaller/faster: `llama3.1:8b`, `qwen2.5:14b`.)
2. Edit `config.yaml` if your model name differs from the default.
3. Run the agent:
   ```bash
   local-agent                 # interactive CLI
   local-agent "list the files in this folder and summarize the README"
   local-agent --serve         # local web UI at http://127.0.0.1:8765
   ```

To use **LM Studio** instead: start its local server (Settings → Local
Server), then in `config.yaml` set `lmstudio.enabled: true` (and optionally
`ollama.enabled: false`). If you turned on LM Studio's optional "require API
key" setting for the local server, put that key in `.env` as
`LMSTUDIO_API_KEY=...`; otherwise leave it blank.

To add a **cloud fallback**, set `enabled: true` on the `openai` and/or
`anthropic` provider entries and put the corresponding API key in `.env`.
Cloud providers are only ever called if every local provider fails.

## Windows quick start (LM Studio, no Python required)

1. Install [LM Studio](https://lmstudio.ai/) for Windows, download a model
   from its "Discover" tab (e.g. `qwen2.5-32b-instruct`), and start the
   **Local Server** (the sidebar tab with the `<->` icon) — note the port,
   `1234` by default.
2. Download the latest `local-agent-portable-windows.zip` from this repo's
   [Releases](../../releases) (or a workflow run of
   `.github/workflows/build-portable.yml`) and unzip it anywhere.
3. Double-click `Start-Agent.bat`. On first run it copies the bundled
   `config.example.yaml`/`.env.example` to `config.yaml`/`.env` for you, then
   launches the web UI in your browser.
4. Edit `config.yaml`: set `lmstudio.enabled: true` (and `ollama.enabled:
   false` if Ollama isn't also installed). Save, close the console window,
   and double-click `Start-Agent.bat` again.
5. Ask it to build something, e.g. *"Create a fully working to-do list web
   app with HTML/CSS/JS in this folder and open it in the browser tool to
   verify it works."* The agent can run shell commands (npm, git, ...),
   fetch real assets and docs from the internet, and edit its own project
   files — no cloud API key is required for any of this.

## Configuration

All settings live in `config.yaml` (see `config/config.example.yaml` for
the full annotated version):

```yaml
providers:
  - name: ollama
    type: openai_compatible
    base_url: http://localhost:11434/v1
    model: qwen2.5:32b-instruct
    enabled: true
  - name: openai
    type: openai_compatible
    base_url: https://api.openai.com/v1
    api_key_env: OPENAI_API_KEY
    model: gpt-4o-mini
    enabled: false

agent:
  workspace: .        # folder the agent may read/write/execute within
  max_steps: 25
```

`AGENT_CONFIG=/path/to/config.yaml` (env var) or `--config` (CLI flag) can
point at a config file outside the current directory.

## Built-in skills (tools)

| Tool | What it does |
|---|---|
| `read_file` / `write_file` / `edit_file` / `list_dir` / `search_files` | Filesystem access, confined to the configured workspace |
| `run_shell` | Run any shell command (builds, tests, git, package managers, ...) |
| `run_python` | Execute a Python snippet in a subprocess |
| `browser_goto` / `browser_click` / `browser_type` / `browser_read` / `browser_screenshot` / `browser_eval_js` / `browser_list_links` | Drive the built-in Chromium browser |
| `web_search` / `web_fetch` | Search the web (DuckDuckGo, no API key) and download page text |
| `memory_set` / `memory_get` / `memory_list` | Persist notes/facts across steps and sessions |
| `todo_add` / `todo_complete` / `todo_list` | Track a running checklist for multi-step tasks |

Adding a new skill means writing a small `Tool(name, description,
parameters, handler)` in `agent/tools/` and registering it in
`agent/core/session.py` — no separate plugin server or IPC protocol needed.

## Portable Windows build

You don't need Python installed on the machine you want to *run* the agent
on. A portable, double-click build is produced by:

```bash
pip install -e ".[build]"
python packaging/build_portable.py
```

This produces `dist/local-agent/` (the folder to distribute) containing
`local-agent.exe`, a bundled Chromium under `playwright-browsers/`, and
`Start-Agent.bat` — the single file a user double-clicks to launch the web
UI. Zip the folder (`dist/local-agent-portable-<os>.zip`) to share it.

PyInstaller cannot cross-compile a Windows `.exe` from Linux/macOS, so to
get the Windows build either run the command above **on Windows**, or
trigger the included GitHub Actions workflow
(`.github/workflows/build-portable.yml`, runs on `windows-latest`) via
"Run workflow" or by pushing a `v*` tag — it uploads
`local-agent-portable-windows.zip` as a build artifact (and as a release
asset for tags).

## Development

```bash
pip install -e ".[dev]"
pytest
```

Tests mock all network calls (no real Ollama/LM Studio/cloud server is
required to run the suite).

## Architecture

```
agent/
  config.py              # YAML + env config, local-first provider ordering
  providers/              # LLM backends: openai_compatible (Ollama/LM Studio/OpenAI), anthropic
    router.py             # tries providers in order, falls back on failure
  core/
    agent_loop.py          # tool-calling ReAct-style loop (structured + text fallback)
    session.py              # wires config + tools + provider router together
  tools/                  # built-in skills (filesystem, shell, python, browser, web, memory, todo)
  cli.py                  # interactive/one-shot CLI
  server.py               # minimal FastAPI local web UI
packaging/                # PyInstaller spec + portable build script + Windows launcher
.github/workflows/        # test CI + Windows portable-build CI
```

## Known limitations

- The browser skill automates Chromium via Playwright; it is not a
  from-scratch browser engine.
- Local 27B-32B models are noticeably weaker than frontier cloud models at
  long agentic tool-use chains; the text-fallback tool-call parser and the
  todo/checklist tool exist specifically to make smaller models more
  reliable over multi-step tasks, but you may still need the cloud
  fallback for the hardest tasks.
- `run_shell` and `run_python` execute with the same permissions as
  whatever user runs `local-agent` — there is no additional OS-level
  sandboxing beyond a timeout, matching how Codex CLI's local "auto" mode
  behaves.
