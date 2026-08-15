"""Built-in browser skill, powered by Playwright driving a real Chromium.

We deliberately reuse Chromium via Playwright rather than attempting to
write a browser rendering engine from scratch (which would be a
multi-million line, multi-year undertaking on its own). What we *do* own
is the automation/agent layer on top: a small set of high-level actions
(navigate, click, type, read text, screenshot, download, run JS) that the
agent's tool-calling loop can invoke, exactly the same shape of
capability Codex/OpenAI's "Operator"-style browsing tools expose.

The browser is started lazily on first use and kept alive for the whole
agent session so state (cookies, tabs) persists across steps, then closed
when the session ends via :meth:`BrowserSession.close`.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from agent.tools.base import Tool, ToolResult


class BrowserSession:
    """Lazily-started Playwright Chromium session shared by all browser tools."""

    def __init__(self, headless: bool = True, download_dir: str = "./agent_downloads"):
        self.headless = headless
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self._playwright = None
        self._browser = None
        self._page = None

    def _ensure_started(self):
        if self._page is not None:
            return self._page
        from playwright.sync_api import sync_playwright

        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=self.headless)
        context = self._browser.new_context(accept_downloads=True)
        self._page = context.new_page()
        return self._page

    def close(self):
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()
        self._browser = None
        self._page = None
        self._playwright = None

    # -- actions -----------------------------------------------------
    def goto(self, url: str) -> str:
        page = self._ensure_started()
        if not url.startswith(("http://", "https://", "file://")):
            url = "https://" + url
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        return f"Loaded {page.url} (title: {page.title()})"

    def read_text(self, selector: Optional[str] = None, max_chars: int = 4000) -> str:
        page = self._ensure_started()
        if selector:
            locator = page.locator(selector).first
            text = locator.inner_text(timeout=10000)
        else:
            text = page.inner_text("body", timeout=10000)
        text = " ".join(text.split())
        return text[:max_chars]

    def click(self, selector: str) -> str:
        page = self._ensure_started()
        page.click(selector, timeout=10000)
        return f"Clicked '{selector}', now at {page.url}"

    def type_text(self, selector: str, text: str, submit: bool = False) -> str:
        page = self._ensure_started()
        page.fill(selector, text, timeout=10000)
        if submit:
            page.press(selector, "Enter")
        return f"Typed into '{selector}'" + (" and pressed Enter" if submit else "")

    def screenshot(self, filename: str = "screenshot.png") -> str:
        page = self._ensure_started()
        out_path = self.download_dir / filename
        page.screenshot(path=str(out_path), full_page=True)
        return f"Saved screenshot to {out_path}"

    def evaluate_js(self, script: str) -> str:
        page = self._ensure_started()
        result = page.evaluate(script)
        return str(result)

    def list_links(self, max_links: int = 30) -> str:
        page = self._ensure_started()
        links = page.eval_on_selector_all(
            "a[href]", "els => els.map(e => e.innerText.trim() + ' -> ' + e.href)"
        )
        return "\n".join(links[:max_links])


def build_browser_tools(headless: bool = True, download_dir: str = "./agent_downloads"):
    """Returns (tools, session). The caller owns the session's lifecycle and
    should call ``session.close()`` when the agent run finishes."""
    session = BrowserSession(headless=headless, download_dir=download_dir)

    def browser_goto(url: str) -> ToolResult:
        return ToolResult(ok=True, output=session.goto(url))

    def browser_read(selector: str = "", max_chars: int = 4000) -> ToolResult:
        return ToolResult(ok=True, output=session.read_text(selector or None, max_chars))

    def browser_click(selector: str) -> ToolResult:
        return ToolResult(ok=True, output=session.click(selector))

    def browser_type(selector: str, text: str, submit: bool = False) -> ToolResult:
        return ToolResult(ok=True, output=session.type_text(selector, text, submit))

    def browser_screenshot(filename: str = "screenshot.png") -> ToolResult:
        return ToolResult(ok=True, output=session.screenshot(filename))

    def browser_eval_js(script: str) -> ToolResult:
        return ToolResult(ok=True, output=session.evaluate_js(script))

    def browser_list_links(max_links: int = 30) -> ToolResult:
        return ToolResult(ok=True, output=session.list_links(max_links))

    tools = [
        Tool(
            name="browser_goto",
            description="Navigate the built-in Chromium browser to a URL.",
            parameters={"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]},
            handler=browser_goto,
        ),
        Tool(
            name="browser_read",
            description="Read visible text from the current page (or a CSS selector within it).",
            parameters={
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "Optional CSS selector"},
                    "max_chars": {"type": "integer"},
                },
                "required": [],
            },
            handler=browser_read,
        ),
        Tool(
            name="browser_click",
            description="Click an element on the current page identified by a CSS selector.",
            parameters={"type": "object", "properties": {"selector": {"type": "string"}}, "required": ["selector"]},
            handler=browser_click,
        ),
        Tool(
            name="browser_type",
            description="Type text into an input/textarea identified by a CSS selector, optionally pressing Enter.",
            parameters={
                "type": "object",
                "properties": {
                    "selector": {"type": "string"},
                    "text": {"type": "string"},
                    "submit": {"type": "boolean"},
                },
                "required": ["selector", "text"],
            },
            handler=browser_type,
        ),
        Tool(
            name="browser_screenshot",
            description="Save a full-page screenshot of the current page to the downloads folder.",
            parameters={"type": "object", "properties": {"filename": {"type": "string"}}, "required": []},
            handler=browser_screenshot,
        ),
        Tool(
            name="browser_eval_js",
            description="Evaluate a JavaScript expression in the page context and return the result.",
            parameters={"type": "object", "properties": {"script": {"type": "string"}}, "required": ["script"]},
            handler=browser_eval_js,
        ),
        Tool(
            name="browser_list_links",
            description="List clickable links (text -> href) visible on the current page.",
            parameters={"type": "object", "properties": {"max_links": {"type": "integer"}}, "required": []},
            handler=browser_list_links,
        ),
    ]
    return tools, session
