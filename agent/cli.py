"""Interactive CLI entry point: ``python -m agent`` / ``local-agent``.

Deliberately built on ``prompt_toolkit`` + ``rich`` rather than a heavier
TUI framework so the whole app stays lightweight enough to bundle into a
single portable executable.
"""
from __future__ import annotations

import argparse
import logging
import sys

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from agent.config import load_config
from agent.core.session import AgentSession
from agent.providers.base import ProviderError

console = Console()


def _print_banner(config) -> None:
    providers = ", ".join(p.name for p in config.enabled_providers()) or "(none enabled!)"
    console.print(
        Panel.fit(
            f"[bold cyan]Local Agent Framework[/bold cyan]\n"
            f"Providers (in try-order): [green]{providers}[/green]\n"
            f"Workspace: [yellow]{config.agent.workspace}[/yellow]\n"
            f"Type a task, or 'exit' to quit.",
            title="local-agent",
        )
    )


def run_single(prompt: str, config_path: str | None) -> int:
    config = load_config(config_path)
    with AgentSession(config) as session:
        try:
            result = session.ask(prompt)
        except ProviderError as exc:
            console.print(f"[bold red]No provider available:[/bold red] {exc}")
            return 1
        console.print(Markdown(result.final_answer))
        return 0


def run_repl(config_path: str | None) -> int:
    config = load_config(config_path)
    _print_banner(config)
    with AgentSession(config) as session:
        while True:
            try:
                prompt = console.input("[bold green]you> [/bold green]")
            except (EOFError, KeyboardInterrupt):
                console.print("\n[dim]bye![/dim]")
                break
            if prompt.strip().lower() in {"exit", "quit"}:
                break
            if not prompt.strip():
                continue
            try:
                with console.status("[bold blue]thinking...[/bold blue]"):
                    result = session.ask(prompt)
            except ProviderError as exc:
                console.print(f"[bold red]No provider available:[/bold red] {exc}")
                continue
            for step in result.steps:
                if step.role == "tool":
                    console.print(f"[dim]  -> {step.tool_name}: {step.content[:300]}[/dim]")
            console.print(Panel(Markdown(result.final_answer), title="agent", border_style="cyan"))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="local-agent", description="Local-first agentic framework")
    parser.add_argument("prompt", nargs="?", help="Run a single task non-interactively")
    parser.add_argument("--config", dest="config_path", help="Path to config.yaml")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    parser.add_argument("--serve", action="store_true", help="Launch the local web UI instead of the CLI")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARNING)

    if args.serve:
        from agent.server import serve

        serve(host=args.host, port=args.port, config_path=args.config_path)
        return 0

    if args.prompt:
        return run_single(args.prompt, args.config_path)
    return run_repl(args.config_path)


if __name__ == "__main__":
    sys.exit(main())
