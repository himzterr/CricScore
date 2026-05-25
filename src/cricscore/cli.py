"""CricScore command-line entry point.

Default: launch the Textual TUI for the given URL.
``--json``: skip the TUI, print parsed match data as JSON.
``--summary``: skip the TUI, print a one-screen human summary.
No URL: launch the TUI on the URL input screen.
"""

from __future__ import annotations

import json
import sys

import typer
from rich.console import Console

from cricscore import __version__
from cricscore.api.client import ESPNCricinfoClient, ScorecardFetchError
from cricscore.models import Match
from cricscore.url_parser import InvalidUrlError, parse_match_url

app = typer.Typer(
    add_completion=False,
    no_args_is_help=False,
    help="CricScore — a polished TUI for ESPNCricinfo scorecards.",
)

_console = Console()
_err_console = Console(stderr=True, style="bold red")


@app.command()
def main(
    url: str = typer.Argument(
        None,
        metavar="[URL]",
        help="ESPNCricinfo full-scorecard URL. Omit to open the in-app input screen.",
    ),
    as_json: bool = typer.Option(
        False,
        "--json",
        help="Skip the TUI; print the parsed match as JSON.",
    ),
    summary: bool = typer.Option(
        False,
        "--summary",
        help="Skip the TUI; print a one-screen human summary.",
    ),
    show_version: bool = typer.Option(
        False, "--version", help="Print the installed CricScore version and exit."
    ),
) -> None:
    """Default action launches the TUI; use --json or --summary for non-interactive output."""
    if show_version:
        _console.print(f"cricscore {__version__}")
        raise typer.Exit()

    match_ref = None
    if url:
        try:
            match_ref = parse_match_url(url)
        except InvalidUrlError as exc:
            _err_console.print(f"Invalid URL: {exc}")
            raise typer.Exit(code=2) from None

    if as_json or summary:
        if match_ref is None:
            _err_console.print("--json and --summary require a URL argument.")
            raise typer.Exit(code=2)
        _run_non_interactive(match_ref, as_json=as_json)
        return

    # Default: launch the TUI.
    from cricscore.tui.app import CricScoreApp

    CricScoreApp(match_ref=match_ref).run()


def _run_non_interactive(match_ref, *, as_json: bool) -> None:
    client = ESPNCricinfoClient()
    try:
        raw = client.fetch_scorecard(match_ref)
    except ScorecardFetchError as exc:
        _err_console.print(f"Fetch failed: {exc}")
        raise typer.Exit(code=3) from None

    try:
        match = Match.from_scorecard_payload(raw)
    except Exception as exc:
        _err_console.print(f"Could not parse scorecard payload: {exc}")
        raise typer.Exit(code=4) from None

    if as_json:
        json.dump(match.model_dump(mode="json"), sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        _print_summary(match)


def _print_summary(match: Match) -> None:
    title = match.title or match.short_title or f"Match {match.id}"
    ground = match.ground.long_name if match.ground else "venue unknown"
    _console.print(f"[bold green]{title}[/] — [dim]{ground}[/]")
    if match.status_text:
        _console.print(f"  [bold yellow]{match.status_text}[/]")
    for ts in match.teams:
        team_name = ts.team.long_name if ts.team and ts.team.long_name else "?"
        score = ts.score or "-"
        info = f"  ({ts.score_info})" if ts.score_info else ""
        _console.print(f"  [cyan]{team_name}[/]: {score}{info}")
    for inn in match.innings:
        name = inn.team.name if inn.team else f"Innings {inn.inning_number}"
        runs = inn.runs if inn.runs is not None else "-"
        wkts = inn.wickets if inn.wickets is not None else "-"
        overs = inn.overs if inn.overs is not None else "-"
        _console.print(
            f"    [bold]{name}[/] {runs}/{wkts} in {overs} overs "
            f"(batters {len(inn.batting_lineup)}, fow {len(inn.fall_of_wickets)})"
        )


if __name__ == "__main__":
    app()
