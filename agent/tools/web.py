"""Lightweight web fetch/search skill that does not require any API key.

``web_fetch`` downloads a URL and strips it down to readable text.
``web_search`` scrapes DuckDuckGo's HTML-only endpoint (no key required,
unlike Google/Bing APIs) to get a handful of result links + snippets that
the agent can then ``web_fetch`` for full content.
"""
from __future__ import annotations

from typing import List

import requests
from bs4 import BeautifulSoup

from agent.tools.base import Tool, ToolResult

USER_AGENT = "Mozilla/5.0 (compatible; LocalAgentFramework/0.1; +https://github.com/)"


def build_web_tools() -> List[Tool]:
    def web_fetch(url: str, max_chars: int = 6000) -> ToolResult:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        try:
            resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
        except requests.RequestException as exc:
            return ToolResult(ok=False, output=f"Failed to fetch {url}: {exc}")
        if resp.status_code >= 400:
            return ToolResult(ok=False, output=f"HTTP {resp.status_code} fetching {url}")
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = " ".join(soup.get_text(" ").split())
        return ToolResult(ok=True, output=text[:max_chars])

    def web_search(query: str, max_results: int = 5) -> ToolResult:
        try:
            resp = requests.post(
                "https://html.duckduckgo.com/html/",
                data={"q": query},
                headers={"User-Agent": USER_AGENT},
                timeout=20,
            )
        except requests.RequestException as exc:
            return ToolResult(ok=False, output=f"Search failed: {exc}")
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for result in soup.select(".result")[:max_results]:
            title_el = result.select_one(".result__a")
            snippet_el = result.select_one(".result__snippet")
            if not title_el:
                continue
            title = title_el.get_text(" ").strip()
            href = title_el.get("href", "")
            snippet = snippet_el.get_text(" ").strip() if snippet_el else ""
            results.append(f"- {title}\n  {href}\n  {snippet}")
        if not results:
            return ToolResult(ok=True, output="No results found.")
        return ToolResult(ok=True, output="\n".join(results))

    return [
        Tool(
            name="web_fetch",
            description="Download a URL and return its readable text content (HTML stripped).",
            parameters={
                "type": "object",
                "properties": {"url": {"type": "string"}, "max_chars": {"type": "integer"}},
                "required": ["url"],
            },
            handler=web_fetch,
        ),
        Tool(
            name="web_search",
            description="Search the web (DuckDuckGo) and return titles, URLs, and snippets.",
            parameters={
                "type": "object",
                "properties": {"query": {"type": "string"}, "max_results": {"type": "integer"}},
                "required": ["query"],
            },
            handler=web_search,
        ),
    ]
