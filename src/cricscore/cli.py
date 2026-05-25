"""CricScore command-line entry point.

Phase 1 only parses the URL and prints the resolved :class:`MatchRef`. Later
phases will route this into the fetcher and TUI.
"""

from __future__ import annotations

import typer
from rich.console import Console

from cricscore import __version__
from cricscore.url_parser import InvalidUrlError, parse_match_url

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="CricScore — a polished TUI for ESPNCricinfo scorecards.",
)

_console = Console()
_err_console = Console(stderr=True, style="bold red")


@app.command()
def main(
    url: str = typer.Argument(
        ...,
        metavar="URL",
        help="ESPNCricinfo full-scorecard URL.",
    ),
    show_version: bool = typer.Option(
        False, "--version", help="Print the installed CricScore version and exit."
    ),
) -> None:
    """Parse an ESPNCricinfo URL and (eventually) render its scorecard."""
    if show_version:
        _console.print(f"cricscore {__version__}")
        raise typer.Exit()

    try:
        match_ref = parse_match_url(url)
    except InvalidUrlError as exc:
        _err_console.print(f"Invalid URL: {exc}")
        raise typer.Exit(code=2) from None

    _console.print(
        f"[bold green]MatchRef[/]"
        f"(series_id=[cyan]{match_ref.series_id}[/], "
        f"match_id=[cyan]{match_ref.match_id}[/])"
    )
    _console.print("[dim]TUI render coming in Phase 3.[/]")


if __name__ == "__main__":
    app()
