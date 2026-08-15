"""HTML/CSS/JS for the local web chat UI, kept as a plain string (no Jinja
templating engine needed) so the whole thing stays dependency-free and can
be embedded directly into the portable build. Split out of ``server.py`` so
the markup doesn't crowd out the API/route code.
"""
from __future__ import annotations

INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Local Agent</title>
<style>
  :root {
    --bg: #0b0d12;
    --panel: #131722;
    --panel-2: #1a1f2e;
    --border: #262c3d;
    --text: #e7e9ee;
    --muted: #8b93a7;
    --accent: #6d8bff;
    --accent-2: #7c5cff;
    --user: #6d8bff;
    --agent: #34d399;
    --danger: #f87171;
    --ok: #34d399;
  }
  * { box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, Roboto, sans-serif;
    margin: 0;
    min-height: 100vh;
    background:
      radial-gradient(1200px 600px at 15% -10%, rgba(109,139,255,0.18), transparent 60%),
      radial-gradient(1000px 500px at 110% 10%, rgba(124,92,255,0.14), transparent 60%),
      var(--bg);
    color: var(--text);
  }
  .app { max-width: 920px; margin: 0 auto; padding: 1.5rem 1rem 2rem; }
  header.topbar {
    display: flex; align-items: center; justify-content: space-between;
    gap: 0.75rem; margin-bottom: 1rem; flex-wrap: wrap;
  }
  .brand { display: flex; align-items: center; gap: 0.6rem; }
  .brand .logo { font-size: 1.6rem; }
  .brand h1 { font-size: 1.25rem; margin: 0; font-weight: 700; letter-spacing: -0.01em; }
  .topbar-actions { display: flex; align-items: center; gap: 0.5rem; }
  .status-pill {
    display: inline-flex; align-items: center; gap: 0.4rem;
    background: var(--panel-2); border: 1px solid var(--border);
    padding: 0.35rem 0.7rem; border-radius: 999px; font-size: 0.8rem; color: var(--muted);
    cursor: default;
  }
  .status-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--danger); flex: none; }
  .status-dot.ok { background: var(--ok); box-shadow: 0 0 8px rgba(52,211,153,0.7); }
  button.icon-btn, button.ghost-btn {
    background: var(--panel-2); border: 1px solid var(--border); color: var(--text);
    padding: 0.4rem 0.7rem; border-radius: 8px; cursor: pointer; font-size: 0.85rem;
    display: inline-flex; align-items: center; gap: 0.35rem; transition: border-color .15s, transform .05s;
  }
  button.icon-btn:hover, button.ghost-btn:hover { border-color: var(--accent); }
  button.icon-btn:active, button.ghost-btn:active { transform: scale(0.97); }

  .card {
    background: linear-gradient(180deg, var(--panel), var(--panel-2));
    border: 1px solid var(--border); border-radius: 14px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.35);
  }

  #log {
    padding: 1.1rem; height: 58vh; overflow-y: auto; scroll-behavior: smooth;
  }
  #log:empty { display: none; }
  .empty-state {
    display: flex; flex-direction: column; align-items: center; text-align: center;
    justify-content: center; height: 58vh; padding: 2rem 1.5rem; gap: 0.5rem;
  }
  .empty-state.hidden { display: none; }
  .empty-state-icon {
    font-size: 2.4rem; width: 72px; height: 72px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center; margin-bottom: 0.4rem;
    background: radial-gradient(circle at 30% 30%, rgba(109,139,255,0.35), rgba(124,92,255,0.12));
    border: 1px solid var(--border);
  }
  .empty-state h2 { margin: 0; font-size: 1.15rem; font-weight: 700; }
  .empty-state .sub { color: var(--muted); font-size: 0.88rem; max-width: 34rem; margin: 0; }
  .empty-state-status {
    display: inline-flex; align-items: center; gap: 0.4rem; font-size: 0.82rem; color: var(--muted);
    margin: 0.3rem 0 0.6rem;
  }
  .empty-state-status.ok { color: var(--ok); }
  .empty-state-status.bad { color: var(--danger); }
  button.primary-btn {
    background: linear-gradient(135deg, var(--accent), var(--accent-2)); color: white; border: none;
    padding: 0.7rem 1.4rem; border-radius: 10px; font-weight: 600; font-size: 0.9rem; cursor: pointer;
    box-shadow: 0 8px 24px rgba(109,139,255,0.25); transition: transform .05s;
  }
  button.primary-btn:active { transform: scale(0.97); }
  .msg { display: flex; gap: 0.6rem; margin: 0 0 1rem; align-items: flex-start; }
  .msg .avatar {
    width: 30px; height: 30px; border-radius: 50%; flex: none;
    display: flex; align-items: center; justify-content: center; font-size: 0.95rem;
    background: var(--panel-2); border: 1px solid var(--border);
  }
  .msg.user .avatar { background: rgba(109,139,255,0.15); }
  .msg.agent .avatar { background: rgba(52,211,153,0.15); }
  .bubble { max-width: 100%; }
  .bubble-head { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.2rem; }
  .bubble-who { font-weight: 600; font-size: 0.82rem; }
  .msg.user .bubble-who { color: var(--user); }
  .msg.agent .bubble-who { color: var(--agent); }
  .bubble-time { color: var(--muted); font-size: 0.72rem; }
  .bubble-content {
    background: var(--panel-2); border: 1px solid var(--border); border-radius: 10px;
    padding: 0.6rem 0.8rem; line-height: 1.5; font-size: 0.92rem; white-space: pre-wrap; word-wrap: break-word;
  }
  .msg.error .bubble-content { border-color: var(--danger); color: #ffd7d7; }
  .bubble-content code {
    background: #0d1017; border: 1px solid var(--border); border-radius: 4px;
    padding: 0.1rem 0.35rem; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.85em;
  }
  .bubble-content pre {
    background: #0d1017; border: 1px solid var(--border); border-radius: 8px;
    padding: 0.7rem; overflow-x: auto; margin: 0.4rem 0;
  }
  .bubble-content pre code { border: none; padding: 0; background: none; }
  .msg-actions { margin-top: 0.3rem; display: flex; gap: 0.4rem; }
  .msg-actions button {
    background: none; border: none; color: var(--muted); cursor: pointer; font-size: 0.72rem; padding: 0;
  }
  .msg-actions button:hover { color: var(--text); text-decoration: underline; }

  details.tool-step {
    margin: 0.3rem 0; background: #0d1017; border: 1px solid var(--border); border-radius: 8px;
    padding: 0.35rem 0.6rem; font-size: 0.8rem; color: var(--muted);
  }
  details.tool-step summary { cursor: pointer; color: #a9b3c9; }
  details.tool-step pre { white-space: pre-wrap; margin: 0.4rem 0 0; }

  .typing { display: inline-flex; gap: 0.25rem; align-items: center; }
  .typing span {
    width: 6px; height: 6px; border-radius: 50%; background: var(--agent); opacity: 0.4;
    animation: blink 1.1s infinite ease-in-out;
  }
  .typing span:nth-child(2) { animation-delay: 0.15s; }
  .typing span:nth-child(3) { animation-delay: 0.3s; }
  @keyframes blink { 0%, 80%, 100% { opacity: 0.25; } 40% { opacity: 1; } }

  form#f { display: flex; gap: 0.6rem; margin-top: 0.9rem; align-items: flex-end; }
  #prompt {
    flex: 1; resize: none; max-height: 160px; min-height: 44px;
    padding: 0.65rem 0.8rem; border-radius: 10px; border: 1px solid var(--border);
    background: var(--panel-2); color: var(--text); font-family: inherit; font-size: 0.92rem; line-height: 1.4;
  }
  #prompt:focus { outline: none; border-color: var(--accent); }
  button#send {
    padding: 0.65rem 1.3rem; border-radius: 10px; border: none; cursor: pointer;
    background: linear-gradient(135deg, var(--accent), var(--accent-2)); color: white; font-weight: 600;
    font-size: 0.92rem;
  }
  button#send:disabled { opacity: 0.6; cursor: not-allowed; }

  /* Settings modal */
  .modal-backdrop {
    position: fixed; inset: 0; background: rgba(4,6,10,0.6); backdrop-filter: blur(2px);
    display: none; align-items: flex-start; justify-content: center; padding: 4vh 1rem; z-index: 20;
  }
  .modal-backdrop.open { display: flex; }
  .modal {
    width: min(640px, 100%); max-height: 90vh; overflow-y: auto; padding: 1.2rem 1.3rem 1.4rem;
  }
  .modal h2 { margin: 0 0 0.2rem; font-size: 1.1rem; }
  .modal .sub { color: var(--muted); font-size: 0.82rem; margin: 0 0 1rem; }
  .modal-close { float: right; }
  .section { margin-bottom: 1.2rem; }
  .section h3 { font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.04em; color: var(--muted); margin: 0 0 0.6rem; }
  .server-row {
    border: 1px solid var(--border); border-radius: 10px; padding: 0.6rem 0.75rem; margin-bottom: 0.55rem;
    background: var(--panel-2);
  }
  .server-row .row-head { display: flex; align-items: center; justify-content: space-between; gap: 0.5rem; }
  .server-row .row-head .name { font-weight: 600; font-size: 0.9rem; }
  .server-row .row-head .url { color: var(--muted); font-size: 0.75rem; }
  .badge { font-size: 0.7rem; padding: 0.1rem 0.5rem; border-radius: 999px; border: 1px solid var(--border); }
  .badge.ok { color: var(--ok); border-color: rgba(52,211,153,0.4); }
  .badge.bad { color: var(--danger); border-color: rgba(248,113,113,0.4); }
  .model-list { display: flex; flex-wrap: wrap; gap: 0.4rem; margin-top: 0.5rem; }
  .model-chip {
    background: #0d1017; border: 1px solid var(--border); color: var(--text);
    padding: 0.3rem 0.6rem; border-radius: 8px; font-size: 0.78rem; cursor: pointer;
  }
  .model-chip:hover { border-color: var(--accent); }
  .model-chip.active { border-color: var(--accent); color: var(--accent); }

  .provider-row {
    display: grid; grid-template-columns: auto 1fr 1fr auto; gap: 0.5rem; align-items: center;
    padding: 0.5rem 0.1rem; border-bottom: 1px solid var(--border); font-size: 0.82rem;
  }
  .provider-row:last-child { border-bottom: none; }
  .provider-row input[type=text] {
    width: 100%; padding: 0.35rem 0.5rem; border-radius: 6px; border: 1px solid var(--border);
    background: #0d1017; color: var(--text); font-size: 0.8rem;
  }
  .switch { position: relative; display: inline-block; width: 34px; height: 19px; flex: none; }
  .switch input { opacity: 0; width: 0; height: 0; }
  .slider {
    position: absolute; cursor: pointer; inset: 0; background: #2a3145; border-radius: 999px; transition: .15s;
  }
  .slider::before {
    content: ""; position: absolute; height: 14px; width: 14px; left: 2.5px; bottom: 2.5px;
    background: white; border-radius: 50%; transition: .15s;
  }
  .switch input:checked + .slider { background: var(--accent); }
  .switch input:checked + .slider::before { transform: translateX(15px); }

  .custom-form { display: grid; grid-template-columns: 1fr 1fr 1fr auto; gap: 0.5rem; }
  .custom-form input {
    padding: 0.45rem 0.6rem; border-radius: 8px; border: 1px solid var(--border);
    background: #0d1017; color: var(--text); font-size: 0.82rem;
  }
  .hint { color: var(--muted); font-size: 0.75rem; margin-top: 0.4rem; }
  .toast {
    position: fixed; bottom: 1.2rem; left: 50%; transform: translateX(-50%);
    background: var(--panel-2); border: 1px solid var(--border); padding: 0.5rem 1rem; border-radius: 8px;
    font-size: 0.82rem; opacity: 0; pointer-events: none; transition: opacity .2s; z-index: 30;
  }
  .toast.show { opacity: 1; }

  @media (max-width: 620px) {
    .provider-row { grid-template-columns: auto 1fr auto; }
    .provider-row .col-url { display: none; }
    .custom-form { grid-template-columns: 1fr; }
  }
</style>
</head>
<body>
  <div class="app">
    <header class="topbar">
      <div class="brand">
        <span class="logo">🤖</span>
        <h1>Local Agent Framework</h1>
      </div>
      <div class="topbar-actions">
        <span class="status-pill" id="statusPill" title="Active model provider">
          <span class="status-dot" id="statusDot"></span>
          <span id="statusText">checking...</span>
        </span>
        <button class="icon-btn" id="clearBtn" title="Clear chat">🗑️ Clear</button>
        <button class="icon-btn" id="settingsBtn" title="Configure local models">⚙️ Settings</button>
      </div>
    </header>

    <div class="card">
      <div class="empty-state" id="emptyState">
        <div class="empty-state-icon">🔌</div>
        <h2>Connect a local model to get started</h2>
        <p class="sub">This runs entirely on your machine — no cloud API key required. Point it at LM Studio, Ollama, or any OpenAI-compatible server.</p>
        <div class="empty-state-status" id="emptyStatus">
          <span class="status-dot" id="emptyStatusDot"></span>
          <span id="emptyStatusText">checking...</span>
        </div>
        <button class="primary-btn" id="connectBtn">⚙️ Connect a local model</button>
      </div>
      <div id="log"></div>
      <form id="f">
        <textarea id="prompt" rows="1" autocomplete="off" placeholder="Ask the agent to do something... (Enter to send, Shift+Enter for newline)"></textarea>
        <button type="submit" id="send">Send</button>
      </form>
    </div>
  </div>

  <div class="modal-backdrop" id="modalBackdrop">
    <div class="card modal">
      <button class="icon-btn modal-close" id="closeSettings">✕</button>
      <h2>Local model settings</h2>
      <p class="sub">Scan for locally running model servers (Ollama, LM Studio, and other
        OpenAI-compatible runtimes) and pick which one the agent should use.</p>

      <div class="section">
        <h3>Discover local servers</h3>
        <button class="ghost-btn" id="scanBtn">🔍 Scan localhost for running servers</button>
        <div id="scanResults"></div>
      </div>

      <div class="section">
        <h3>Configured providers</h3>
        <div id="providerList"></div>
      </div>

      <div class="section">
        <h3>Add a custom server</h3>
        <div class="custom-form">
          <input id="customName" placeholder="name (e.g. myserver)" />
          <input id="customUrl" placeholder="base URL (http://localhost:PORT/v1)" />
          <input id="customModel" placeholder="model id" />
          <button class="ghost-btn" id="customAddBtn">Add &amp; use</button>
        </div>
        <p class="hint">Works with any server exposing an OpenAI-compatible <code>/v1/chat/completions</code> endpoint (vLLM, text-generation-webui, LocalAI, LiteLLM, etc).</p>
      </div>
    </div>
  </div>

  <div class="toast" id="toast"></div>

<script>
const log = document.getElementById('log');
const form = document.getElementById('f');
const input = document.getElementById('prompt');
const sendBtn = document.getElementById('send');
const clearBtn = document.getElementById('clearBtn');
const statusDot = document.getElementById('statusDot');
const statusText = document.getElementById('statusText');
const settingsBtn = document.getElementById('settingsBtn');
const closeSettings = document.getElementById('closeSettings');
const modalBackdrop = document.getElementById('modalBackdrop');
const scanBtn = document.getElementById('scanBtn');
const scanResults = document.getElementById('scanResults');
const providerList = document.getElementById('providerList');
const toast = document.getElementById('toast');
const emptyState = document.getElementById('emptyState');
const emptyStatusDot = document.getElementById('emptyStatusDot');
const emptyStatusText = document.getElementById('emptyStatusText');
const connectBtn = document.getElementById('connectBtn');

function openSettings() {
  modalBackdrop.classList.add('open');
  loadProviders();
}

function updateEmptyState() {
  emptyState.classList.toggle('hidden', log.children.length > 0);
}

function showToast(msg) {
  toast.textContent = msg;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 2200);
}

function escapeHtml(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

// Small, dependency-free markdown-lite renderer: fenced code blocks, inline
// code, bold/italic, and links -- enough for typical agent replies without
// pulling in a full markdown library.
function renderMarkdown(text) {
  const blocks = [];
  let placeholder = text.replace(/```([a-zA-Z0-9_+-]*)\\n?([\\s\\S]*?)```/g, (m, lang, code) => {
    const idx = blocks.length;
    blocks.push('<pre><code>' + escapeHtml(code.trim()) + '</code></pre>');
    return '\\u0000' + idx + '\\u0000';
  });
  let escaped = escapeHtml(placeholder);
  escaped = escaped.replace(/`([^`]+)`/g, '<code>$1</code>');
  escaped = escaped.replace(/\\*\\*([^*]+)\\*\\*/g, '<strong>$1</strong>');
  escaped = escaped.replace(/(^|[^*])\\*([^*]+)\\*/g, '$1<em>$2</em>');
  escaped = escaped.replace(/\\[([^\\]]+)\\]\\((https?:\\/\\/[^\\s)]+)\\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
  escaped = escaped.replace(/\\u0000(\\d+)\\u0000/g, (m, idx) => blocks[Number(idx)]);
  return escaped;
}

function timeNow() {
  return new Date().toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});
}

function appendMessage(role, text, opts) {
  opts = opts || {};
  const wrap = document.createElement('div');
  wrap.className = 'msg ' + role + (opts.error ? ' error' : '');
  const avatar = role === 'user' ? '🧑' : (opts.error ? '⚠️' : '🤖');
  const who = role === 'user' ? 'you' : 'agent';
  wrap.innerHTML =
    '<div class="avatar">' + avatar + '</div>' +
    '<div class="bubble">' +
      '<div class="bubble-head"><span class="bubble-who">' + who + '</span>' +
      '<span class="bubble-time">' + timeNow() + '</span></div>' +
      '<div class="bubble-content">' + renderMarkdown(text) + '</div>' +
    '</div>';
  log.appendChild(wrap);
  updateEmptyState();
  if (role === 'agent' && !opts.error) {
    const actions = document.createElement('div');
    actions.className = 'msg-actions';
    const copyBtn = document.createElement('button');
    copyBtn.textContent = 'copy';
    copyBtn.onclick = () => { navigator.clipboard.writeText(text); showToast('Copied to clipboard'); };
    actions.appendChild(copyBtn);
    wrap.querySelector('.bubble').appendChild(actions);
  }
  log.scrollTop = log.scrollHeight;
  return wrap;
}

function appendTyping() {
  const wrap = document.createElement('div');
  wrap.className = 'msg agent';
  wrap.id = 'typingIndicator';
  wrap.innerHTML =
    '<div class="avatar">🤖</div>' +
    '<div class="bubble"><div class="bubble-content"><span class="typing"><span></span><span></span><span></span></span></div></div>';
  log.appendChild(wrap);
  log.scrollTop = log.scrollHeight;
}

function removeTyping() {
  const el = document.getElementById('typingIndicator');
  if (el) el.remove();
}

function appendToolSteps(steps) {
  const toolSteps = steps.filter(s => s.role === 'tool');
  if (!toolSteps.length) return;
  const details = document.createElement('details');
  details.className = 'tool-step';
  const summary = document.createElement('summary');
  summary.textContent = toolSteps.length + ' tool call' + (toolSteps.length > 1 ? 's' : '') + ' (click to expand)';
  details.appendChild(summary);
  for (const step of toolSteps) {
    const pre = document.createElement('pre');
    pre.textContent = step.tool_name + ' -> ' + step.content.slice(0, 800);
    details.appendChild(pre);
  }
  log.appendChild(details);
  log.scrollTop = log.scrollHeight;
}

input.addEventListener('input', () => {
  input.style.height = 'auto';
  input.style.height = Math.min(input.scrollHeight, 160) + 'px';
});
input.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    form.requestSubmit();
  }
});

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const prompt = input.value.trim();
  if (!prompt) return;
  appendMessage('user', prompt);
  input.value = '';
  input.style.height = 'auto';
  sendBtn.disabled = true;
  appendTyping();
  try {
    const resp = await fetch('/api/chat', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({prompt})
    });
    const data = await resp.json();
    removeTyping();
    appendToolSteps(data.steps || []);
    appendMessage('agent', data.final_answer, {error: !!data.error});
  } catch (err) {
    removeTyping();
    appendMessage('agent', 'Request failed: ' + err, {error: true});
  } finally {
    sendBtn.disabled = false;
    input.focus();
  }
});

clearBtn.addEventListener('click', async () => {
  log.innerHTML = '';
  updateEmptyState();
  try { await fetch('/api/chat/clear', {method: 'POST'}); } catch (err) {}
  showToast('Chat cleared');
});

function setStatusIndicators(dotOk, text) {
  statusDot.classList.toggle('ok', dotOk);
  statusText.textContent = text;
  emptyStatusDot.classList.toggle('ok', dotOk);
  emptyStatusText.textContent = dotOk ? 'Connected \\u00b7 ' + text : text;
}

async function refreshStatus() {
  try {
    const resp = await fetch('/api/providers');
    const data = await resp.json();
    const active = data.providers.find(p => p.active);
    if (active) {
      setStatusIndicators(true, active.name + ' \\u00b7 ' + active.model);
    } else {
      setStatusIndicators(false, 'No provider connected \\u2014 click Connect to set one up');
    }
    return data.providers;
  } catch (err) {
    setStatusIndicators(false, 'Server unreachable');
    return [];
  }
}

function providerRow(p) {
  const row = document.createElement('div');
  row.className = 'provider-row';
  row.innerHTML =
    '<label class="switch"><input type="checkbox" ' + (p.enabled ? 'checked' : '') + ' data-role="enabled"><span class="slider"></span></label>' +
    '<input type="text" class="col-url" value="' + escapeHtml(p.base_url) + '" data-role="base_url" placeholder="base URL" />' +
    '<input type="text" value="' + escapeHtml(p.model) + '" data-role="model" placeholder="model" />' +
    '<button class="icon-btn" data-role="save">Save</button>';
  row.querySelector('[data-role=save]').addEventListener('click', async () => {
    const enabled = row.querySelector('[data-role=enabled]').checked;
    const base_url = row.querySelector('[data-role=base_url]').value.trim();
    const model = row.querySelector('[data-role=model]').value.trim();
    await saveProvider(p.name, {enabled, base_url, model});
  });
  const label = document.createElement('div');
  label.style.fontWeight = '600';
  label.textContent = p.name;
  row.insertBefore(label, row.firstChild);
  return row;
}

async function saveProvider(name, payload) {
  try {
    const resp = await fetch('/api/providers/' + encodeURIComponent(name), {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload)
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      showToast('Failed: ' + (err.detail || resp.statusText));
      return null;
    }
    const data = await resp.json();
    renderProviderList(data.providers);
    await refreshStatus();
    showToast(name + ' updated');
    return data;
  } catch (err) {
    showToast('Failed: ' + err);
    return null;
  }
}

function renderProviderList(providers) {
  providerList.innerHTML = '';
  for (const p of providers) {
    providerList.appendChild(providerRow(p));
  }
}

async function loadProviders() {
  const providers = await refreshStatus();
  renderProviderList(providers);
}

function serverRow(server) {
  const row = document.createElement('div');
  row.className = 'server-row';
  const badge = server.reachable ? '<span class="badge ok">running</span>' : '<span class="badge bad">not found</span>';
  let modelsHtml = '';
  if (server.reachable && server.models.length) {
    modelsHtml = '<div class="model-list">' + server.models.map(m =>
      '<span class="model-chip" data-model="' + escapeHtml(m) + '">' + escapeHtml(m) + '</span>'
    ).join('') + '</div>';
  } else if (server.reachable) {
    modelsHtml = '<div class="hint">Reachable, but no models reported.</div>';
  } else if (server.error) {
    modelsHtml = '<div class="hint">' + escapeHtml(server.error) + '</div>';
  }
  row.innerHTML =
    '<div class="row-head"><span><span class="name">' + escapeHtml(server.name) + '</span> ' +
    '<span class="url">' + escapeHtml(server.base_url) + '</span></span>' + badge + '</div>' + modelsHtml;
  row.querySelectorAll('.model-chip').forEach(chip => {
    chip.addEventListener('click', async () => {
      row.querySelectorAll('.model-chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      await saveProvider(server.name, {
        base_url: server.base_url,
        model: chip.dataset.model,
        enabled: true,
        exclusive: true,
      });
    });
  });
  return row;
}

scanBtn.addEventListener('click', async () => {
  scanBtn.disabled = true;
  scanBtn.textContent = 'Scanning...';
  scanResults.innerHTML = '';
  try {
    const resp = await fetch('/api/discover');
    const data = await resp.json();
    for (const server of data.servers) {
      scanResults.appendChild(serverRow(server));
    }
  } catch (err) {
    showToast('Scan failed: ' + err);
  } finally {
    scanBtn.disabled = false;
    scanBtn.textContent = '🔍 Scan localhost for running servers';
  }
});

document.getElementById('customAddBtn').addEventListener('click', async () => {
  const name = document.getElementById('customName').value.trim();
  const base_url = document.getElementById('customUrl').value.trim();
  const model = document.getElementById('customModel').value.trim();
  if (!name || !base_url || !model) {
    showToast('Fill in name, URL, and model');
    return;
  }
  const data = await saveProvider(name, {base_url, model, enabled: true, exclusive: true});
  if (data) {
    document.getElementById('customName').value = '';
    document.getElementById('customUrl').value = '';
    document.getElementById('customModel').value = '';
  }
});

settingsBtn.addEventListener('click', openSettings);
connectBtn.addEventListener('click', () => {
  openSettings();
  scanBtn.click();
});
closeSettings.addEventListener('click', () => modalBackdrop.classList.remove('open'));
modalBackdrop.addEventListener('click', (e) => { if (e.target === modalBackdrop) modalBackdrop.classList.remove('open'); });

refreshStatus();
updateEmptyState();
input.focus();
</script>
</body>
</html>
"""
