"""shoruiko CLI — prose AI-pattern stripping from the command line."""

from __future__ import annotations

import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from shoruiko.core import (
    Mode,
    mode_light,
    mode_medium,
    mode_aggressive,
    shoruiko,
    shoruiko_file,
    Stats,
)

app = typer.Typer(
    name="shoruiko",
    help="Strip AI writing patterns from natural-language prose.",
    no_args_is_help=True,
)
console = Console()


def _pick_mode(light: bool, aggressive: bool) -> Mode:
    if aggressive:
        return mode_aggressive()
    if light:
        return mode_light()
    return mode_medium()


def _render_stats(stats: Stats) -> None:
    """Render a rich stats table."""
    changes = []
    if stats.chatbot_lines:
        changes.append(("Chatbot artifacts", stats.chatbot_lines))
    if stats.sycophantic_lines:
        changes.append(("Sycophantic tone", stats.sycophantic_lines))
    if stats.disclaimers:
        changes.append(("Disclaimers", stats.disclaimers))
    if stats.generic_endings:
        changes.append(("Generic endings", stats.generic_endings))
    if stats.filler_substitutions:
        changes.append(("Filler phrases", stats.filler_substitutions))
    if stats.hedging_substitutions:
        changes.append(("Hedging", stats.hedging_substitutions))
    if stats.copula_substitutions:
        changes.append(("Copula avoidance", stats.copula_substitutions))
    if stats.formal_linking_substitutions:
        changes.append(("Formal linking", stats.formal_linking_substitutions))
    if stats.rule_of_three_rewrites:
        changes.append(("Rule of three", stats.rule_of_three_rewrites))
    if stats.contrast_rewrites:
        changes.append(("Exaggerated contrasts", stats.contrast_rewrites))
    if stats.overstructuring_rewrites:
        changes.append(("Overstructuring", stats.overstructuring_rewrites))
    if stats.vocabulary_swaps:
        changes.append(("Vocabulary swaps", stats.vocabulary_swaps))
    if stats.em_dashes_normalized:
        changes.append(("Em-dashes normalized", stats.em_dashes_normalized))
    if stats.passive_rewrites:
        changes.append(("Passive voice", stats.passive_rewrites))

    if not changes:
        console.print("[dim]No AI patterns detected.[/dim]")
        return

    table = Table(title="Changes by Category", show_header=True, header_style="bold cyan")
    table.add_column("Category", style="dim")
    table.add_column("Count", justify="right", style="bold yellow")
    for cat, count in changes:
        table.add_row(cat, str(count))
    console.print(table)
    console.print(
        f"  [bold]{stats.total_changes} changes[/bold]  |  "
        f"{stats.bytes_before:,}B → {stats.bytes_after:,}B  "
        f"([green]-{stats.ratio}%[/green])"
    )


@app.command()
def file(
    path: str = typer.Argument(..., help="Path to a text file"),
    light: bool = typer.Option(False, "--light", "-l", help="Whitespace only"),
    aggressive: bool = typer.Option(
        False, "--aggressive", "-a", help="Deep de-AI-fication"
    ),
    write: bool = typer.Option(
        False, "--write", "-w", help="Overwrite file in place"
    ),
    stats_only: bool = typer.Option(
        False, "--stats", "-s", help="Show only statistics, not output"
    ),
):
    """Process a single prose file."""
    mode = _pick_mode(light, aggressive)
    fpath = Path(path).resolve()

    if not fpath.exists():
        console.print(f"[red]File not found:[/red] {path}")
        raise typer.Exit(1)

    text, stats = shoruiko_file(str(fpath), mode)

    if write:
        if stats.total_changes > 0:
            fpath.write_text(text, encoding="utf-8")
            console.print(f"[green]✓[/green] Wrote {fpath}")
            _render_stats(stats)
        else:
            console.print("[dim]No changes needed.[/dim]")
    else:
        if stats_only:
            _render_stats(stats)
        else:
            sys.stdout.write(text)
            console.print(f"\n[dim]── {stats.total_changes} change(s) ──[/dim]")
            sys.stderr.write(f"\n── {stats.total_changes} change(s) ──\n")


@app.command()
def clip(
    aggressive: bool = typer.Option(
        False, "--aggressive", "-a", help="Deep de-AI-fication"
    ),
):
    """Process text from clipboard (requires pyperclip).

    Copies the result back to clipboard.
    """
    try:
        import pyperclip
    except ImportError:
        console.print(
            "[red]pyperclip not installed.[/red] "
            "Install with: pip install pyperclip"
        )
        raise typer.Exit(1)

    mode = mode_aggressive() if aggressive else mode_medium()
    text = pyperclip.paste()
    if not text.strip():
        console.print("[dim]Clipboard is empty.[/dim]")
        raise typer.Exit(0)

    result, stats = shoruiko(text, mode)
    pyperclip.copy(result)
    console.print(f"[green]✓[/green] Processed clipboard text")
    _render_stats(stats)


@app.command()
def gui():
    """Launch the shoruiko desktop GUI (liquid glass + bento grid)."""
    from shoruiko.gui import launch

    launch()


@app.command()
def version():
    """Show version."""
    from shoruiko import __version__

    console.print(f"shoruiko v{__version__}")
