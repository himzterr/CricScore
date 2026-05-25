"""CricScore command-line entry point.

Phase 2 wires the URL parser into the curl_cffi scraper and pydantic models.
With ``--json`` the parsed :class:`Match` is dumped as JSON; without it, a
small human-readable summary is printed. The TUI render lands in Phase 3.
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
    as_json: bool = typer.Option(
        False,
        "--json",
        help="Print the parsed match as JSON instead of a summary.",
    ),
    show_version: bool = typer.Option(
        False, "--version", help="Print the installed CricScore version and exit."
    ),
) -> None:
    """Parse an ESPNCricinfo URL, fetch the scorecard, and (eventually) render it."""
    if show_version:
        _console.print(f"cricscore {__version__}")
        raise typer.Exit()

    try:
        match_ref = parse_match_url(url)
    except InvalidUrlError as exc:
        _err_console.print(f"Invalid URL: {exc}")
        raise typer.Exit(code=2) from None

    client = ESPNCricinfoClient()
    try:
        raw = client.fetch_scorecard(match_ref)
    except ScorecardFetchError as exc:
        _err_console.print(f"Fetch failed: {exc}")
        raise typer.Exit(code=3) from None

    try:
        match = Match.from_scorecard_payload(raw)
    except Exception as exc:  # pydantic ValidationError or shape errors
        _err_console.print(f"Could not parse scorecard payload: {exc}")
        raise typer.Exit(code=4) from None

    if as_json:
        json.dump(match.model_dump(mode="json"), sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return

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
    _console.print("[dim]TUI render coming in Phase 3.[/]")


if __name__ == "__main__":
    app()
