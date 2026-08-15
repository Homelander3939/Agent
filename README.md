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
- **Two ways to use it:** an interactive CLI (`local-agent`) or a modern
  local web chat UI (`local-agent --serve`) that opens in your browser,
  complete with a **Settings** panel that scans localhost for running
  Ollama/LM Studio/other OpenAI-compatible servers, lists their available
  models, and lets you switch the active model with one click -- no YAML
  editing or restart required. The CLI has the same capability via
  `/providers`, `/use <name>`, and `/set <name> key=value` commands.
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

1. Install [LM Studio](https://lmstudio.ai/), download a model, and start its
   **Local Server** (sidebar tab with the `<->` icon, port `1234` by
   default). This is the default enabled provider, so no config edit is
   needed. If you turned on LM Studio's optional "require API key" setting,
   put that key in `.env` as `LMSTUDIO_API_KEY=...`; otherwise leave it blank.
2. Edit `config.yaml` if your model name differs from the default -- or
   skip this step and use the web UI's **Settings** panel instead (see
   below), which can detect it for you.
3. Run the agent:
   ```bash
   local-agent                 # interactive CLI
   local-agent "list the files in this folder and summarize the README"
   local-agent --serve         # local web UI at http://127.0.0.1:8765
   ```

To use **Ollama** instead: install it, `ollama pull qwen2.5:32b-instruct` (or
another model), then in `config.yaml` set `ollama.enabled: true` (and
optionally `lmstudio.enabled: false`).

To add a **cloud fallback**, set `enabled: true` on the `openai` and/or
`anthropic` provider entries and put the corresponding API key in `.env`.
Cloud providers are only ever called if every local provider fails.

### Configuring your local model from the web UI

You don't have to hand-edit YAML to point the agent at your local model.
Open the web UI (`local-agent --serve`) and click **⚙️ Settings**:

- **🔍 Scan localhost for running servers** probes the well-known ports for
  Ollama, LM Studio, and other OpenAI-compatible local runtimes (vLLM,
  text-generation-webui, LocalAI, ...) and lists which ones are actually
  running right now, along with every model each one currently has
  loaded/pulled.
- Click a model in the results to make it the active provider immediately
  -- no restart required -- and the choice is written back to `config.yaml`
  so it's remembered next time you launch.
- The **Configured providers** list lets you toggle any provider on/off and
  edit its base URL/model directly.
- **Add a custom server** wires up any other OpenAI-compatible endpoint by
  URL if it isn't one of the auto-detected ones.
- The status pill in the header always shows which provider/model is
  currently active.

If `Start-Agent.bat`/`local-agent --serve` is launched while an instance is
already running, it detects that and just opens your existing window instead
of crashing with a "port already in use" error; if the port is held by some
other, unrelated program, it automatically picks the next free port instead.

### Configuring your local model from the CLI

The interactive CLI (`local-agent`) supports the same configuration without
touching YAML or opening a browser:

```text
you> /providers                 # list configured providers
you> /use lmstudio               # make lmstudio the only enabled provider
you> /set lmstudio base_url=http://localhost:1234/v1 model=my-model
you> /help                       # show all commands
```

## Windows quick start (LM Studio, no Python required)

1. Install [LM Studio](https://lmstudio.ai/) for Windows, download a model
   from its "Discover" tab (e.g. `qwen2.5-32b-instruct`), and start the
   **Local Server** (the sidebar tab with the `<->` icon) — note the port,
   `1234` by default. LM Studio is the default provider, so no config
   changes are required to use it.
2. Download the portable build (no Python needed) from this permanent link,
   which always points to the newest automated build from `main`:

   **[`local-agent-portable-windows.zip`](../../releases/latest/download/local-agent-portable-windows.zip)**

   Bookmark that link — it's rebuilt and replaced automatically on every
   change pushed to `main`, so it always serves the latest version. (Tagged
   `vX.Y.Z` releases are also published on the [Releases](../../releases)
   page if you'd rather pin a specific version.) Unzip the download anywhere.
3. Double-click `Start-Agent.bat`. On first run it copies the bundled
   `config.example.yaml`/`.env.example` to `config.yaml`/`.env` for you, then
   launches the web UI in your browser.
4. If LM Studio reports a model name other than `local-model`, click
   **⚙️ Settings → 🔍 Scan localhost for running servers**, then click the
   model shown under `lmstudio` to activate it instantly (no need to edit
   `config.yaml` or restart).
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
  - name: lmstudio
    type: openai_compatible
    base_url: http://localhost:1234/v1
    model: local-model
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
"Run workflow". It runs automatically on every push to `main`, publishing
`local-agent-portable-windows.zip` to a rolling `latest-build` GitHub
Release marked as the repo's "latest" release (permanent link:
`releases/latest/download/local-agent-portable-windows.zip`), and it also
publishes a dedicated versioned release when a `v*` tag is pushed.

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
