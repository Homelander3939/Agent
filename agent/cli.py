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
from rich.table import Table

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
            f"Type a task, '/help' to configure providers/credentials, or 'exit' to quit.",
            title="local-agent",
        )
    )


def _print_providers(session: AgentSession) -> None:
    table = Table(title="Configured providers", header_style="bold cyan")
    table.add_column("name")
    table.add_column("enabled")
    table.add_column("base_url")
    table.add_column("model")
    for p in session.config.providers:
        table.add_row(
            p.name,
            "[green]yes[/green]" if p.enabled else "[dim]no[/dim]",
            p.base_url,
            p.model,
        )
    console.print(table)


def _handle_command(session: AgentSession, line: str) -> bool:
    """Handle a leading-'/' REPL command (provider/credential configuration
    without needing to hand-edit config.yaml or use the web UI). Returns
    True if the line was a recognized command."""
    parts = line.strip().split()
    if not parts:
        return False
    cmd = parts[0].lower()

    if cmd in {"/help", "/?"}:
        console.print(
            "[bold]Commands:[/bold]\n"
            "  /providers                 list configured providers\n"
            "  /use <name>                make <name> the only enabled provider, e.g. [cyan]/use lmstudio[/cyan]\n"
            "  /set <name> key=value ...  update a provider's base_url/model/key, e.g.\n"
            "                             [cyan]/set lmstudio base_url=http://localhost:1234/v1 model=my-model[/cyan]\n"
            "  /help                      show this message\n"
            "  exit                       quit"
        )
        return True

    if cmd == "/providers":
        _print_providers(session)
        return True

    if cmd == "/use":
        if len(parts) != 2:
            console.print("[bold red]Usage:[/bold red] /use <provider-name>")
            return True
        name = parts[1]
        try:
            session.configure_provider(name, enabled=True, exclusive=True)
            console.print(f"[green]{name} is now the active provider.[/green]")
        except ProviderError as exc:
            console.print(f"[bold red]Could not switch:[/bold red] {exc}")
        return True

    if cmd == "/set":
        if len(parts) < 3:
            console.print(
                "[bold red]Usage:[/bold red] /set <name> key=value [key=value ...] "
                "(keys: base_url, model, key)"
            )
            return True
        name = parts[1]
        kwargs: dict = {}
        for pair in parts[2:]:
            if "=" not in pair:
                continue
            key, _, value = pair.partition("=")
            if key == "base_url":
                kwargs["base_url"] = value
            elif key == "model":
                kwargs["model"] = value
            elif key in {"key", "api_key"}:
                kwargs["api_key"] = value
        if not kwargs:
            console.print("[bold red]Nothing to update.[/bold red] Use base_url=/model=/key=")
            return True
        try:
            session.configure_provider(name, **kwargs)
            console.print(f"[green]{name} updated.[/green]")
        except ProviderError as exc:
            console.print(f"[bold red]Could not update:[/bold red] {exc}")
        return True

    return False


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
            if prompt.strip().startswith("/"):
                if not _handle_command(session, prompt):
                    console.print("[bold red]Unknown command.[/bold red] Type /help for a list.")
                continue
            try:
                with console.status("[bold blue]thinking...[/bold blue]"):
                    result = session.ask(prompt)
            except ProviderError as exc:
                console.print(f"[bold red]No provider available:[/bold red] {exc}")
                console.print("[dim]Type /providers to see your providers, or /use <name> to switch (e.g. /use lmstudio).[/dim]")
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
