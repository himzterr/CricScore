# CricScore — Initial Build Plan

## Context

The user is starting a new project, **CricScore**, from an empty directory at `/Users/himzter/Documents/Programming/Projects/CricScore` and an empty GitHub repo at `https://github.com/himzterr/CricScore`. The goal is a polished terminal UI that:

1. Accepts an ESPNCricinfo full-scorecard URL (e.g. `https://www.espncricinfo.com/series/ipl-2026-1510719/kolkata-knight-riders-vs-delhi-capitals-70th-match-1529313/full-scorecard`).
2. Fetches the match data.
3. Renders it in a TUI with nice text effects (animations, gradients, smooth panels).

External constraints already verified this session:

- ESPNCricinfo's HTML pages **and** their `hs-consumer-api.espncricinfo.com` JSON endpoints are gated by Akamai. Plain `curl`/`httpx` both return `403` even with realistic headers — the block is TLS-fingerprint-based, not header-based.
- The URL path encodes everything we need: `seriesId` (`1510719`) and `matchId` (`1529313`) are both extractable with a regex against `/series/<slug>-<id>/.../<slug>-<id>/full-scorecard`.

User-confirmed decisions (this turn):

- **Stack:** Python + Textual + Rich + curl_cffi.
- **MVP scope (Phases 1–3):** Full scorecard only — match header, batting tables, bowling tables, fall of wickets per innings. Live polling and extras come later.

## Recommended Approach

A Python 3.12+ `src/`-layout package named `cricscore`, installable with `pip install -e .`, runnable as `cricscore <url>` (and `python -m cricscore <url>`). Scraping uses **curl_cffi** to impersonate Chrome's TLS handshake and hit the ESPNCricinfo JSON API — much more robust than parsing HTML, and avoids brittle DOM scraping. Textual renders the UI; Rich provides the inline text effects (gradients, spinners, animated tables).

### Tech stack and why each piece earns its place

| Dependency      | Role                                                                  |
| --------------- | --------------------------------------------------------------------- |
| `textual`       | App framework, screens, reactive widgets, CSS-style theming           |
| `rich`          | Inline gradients, spinners, animated tables (bundled with Textual)    |
| `curl_cffi`     | HTTP client that impersonates Chrome's TLS fingerprint → beats Akamai |
| `pydantic`      | Typed models for the parsed scorecard payload                         |
| `typer`         | Tiny CLI wrapper for `cricscore <url>`                                |
| `pytest`        | Tests (URL parser, model coercion, golden-file API parsing)           |
| `ruff` + `mypy` | Lint + types (dev-only)                                               |

### Project layout

```
CricScore/
├── README.md                  # User-facing overview, install, usage
├── PLAN.md                    # Copy of this plan, committed to repo for context
├── pyproject.toml             # Build config + deps + scripts
├── .gitignore                 # Python + venv + .DS_Store + .env
├── .python-version            # 3.12 pin (for pyenv users)
├── src/
│   └── cricscore/
│       ├── __init__.py        # Package version
│       ├── __main__.py        # `python -m cricscore` entry
│       ├── cli.py             # typer app, wires URL → fetcher → TUI
│       ├── url_parser.py      # extract (seriesId, matchId) from URL
│       ├── api/
│       │   ├── __init__.py
│       │   ├── client.py      # curl_cffi-based ESPNCricinfo client
│       │   └── endpoints.py   # URL builders for scorecard / match-info
│       ├── models/
│       │   ├── __init__.py
│       │   └── match.py       # pydantic models: Match, Innings, Batter, Bowler, Fow
│       ├── tui/
│       │   ├── __init__.py
│       │   ├── app.py         # CricScoreApp(App)
│       │   ├── screens/
│       │   │   ├── url_input.py
│       │   │   ├── loading.py
│       │   │   └── scorecard.py
│       │   ├── widgets/
│       │   │   ├── match_header.py
│       │   │   ├── innings_panel.py
│       │   │   ├── batting_table.py
│       │   │   ├── bowling_table.py
│       │   │   └── fow_strip.py
│       │   └── styles.tcss    # Textual CSS (colors, borders, spacing)
│       └── effects/
│           ├── __init__.py
│           ├── typewriter.py  # async char-by-char reveal
│           └── gradient.py    # rich Text gradient helpers
└── tests/
    ├── __init__.py
    ├── test_url_parser.py
    ├── test_models.py
    └── fixtures/
        └── scorecard_1529313.json   # captured live, used for offline tests
```

### Multi-phase roadmap

#### Phase 1 — Scaffolding (the commit that goes up first)

- `pyproject.toml` with deps and `[project.scripts] cricscore = "cricscore.cli:app"`
- `.gitignore`, `.python-version`, `README.md`, `PLAN.md`
- `src/cricscore/__init__.py` (just `__version__ = "0.0.1"`)
- `src/cricscore/url_parser.py` — pure function `parse_match_url(url) -> MatchRef(series_id, match_id)`; raises `InvalidUrlError` otherwise
- `src/cricscore/cli.py` — `typer` app: parses URL, prints `MatchRef` (no TUI yet)
- `src/cricscore/__main__.py` — delegates to `cli.app()`
- `tests/test_url_parser.py` — covers happy path + bad input

**Acceptance:** `pip install -e .` then `cricscore https://www.espncricinfo.com/.../70th-match-1529313/full-scorecard` prints `MatchRef(series_id=1510719, match_id=1529313)`.

#### Phase 2 — Data layer

- `src/cricscore/api/client.py` — `ESPNCricinfoClient` wrapping `curl_cffi.requests.Session(impersonate="chrome")`. Public method: `fetch_scorecard(match_ref) -> dict`.
- `src/cricscore/api/endpoints.py` — `scorecard_url(series_id, match_id)` → `https://hs-consumer-api.espncricinfo.com/v1/pages/match/scorecard?lang=en&seriesId={s}&matchId={m}`.
- `src/cricscore/models/match.py` — pydantic models for the response slice we care about: `Match`, `Innings`, `Batter`, `Bowler`, `FallOfWicket`. Tolerant of missing fields.
- Capture a real response into `tests/fixtures/scorecard_1529313.json` and parse it in `test_models.py`.
- CLI: add `--json` flag that prints the parsed `Match` as JSON (useful for debugging and CI).

**Acceptance:** `cricscore <url> --json` prints structured match data; `pytest` passes against the fixture.

#### Phase 3 — TUI skeleton + scorecard render

- `tui/app.py` boots `CricScoreApp`. If a URL is passed on the CLI it routes straight to `LoadingScreen`; otherwise `URLInputScreen` shows an Input widget.
- `LoadingScreen` shows a centered Rich spinner with a typewriter status line ("Resolving series 1510719…", "Fetching scorecard…").
- `ScorecardScreen` lays out:
  - **Header** (`MatchHeader`): teams, format, venue, toss, result, with a subtle gradient title.
  - **Innings tabs** (one tab per innings via `TabbedContent`).
  - Each tab contains `InningsPanel` = `BattingTable` + `BowlingTable` + `FowStrip`.
- `styles.tcss` defines the palette (deep navy + warm orange accent, easy to retheme).

**Acceptance:** `cricscore <url>` opens the TUI and renders the KKR vs DC scorecard with batting and bowling tables fully populated. `q` quits.

#### Phase 4 — Text effects & polish

- Typewriter reveal on the match-header title (`effects/typewriter.py`).
- Gradient run/wicket totals (`effects/gradient.py`).
- Animated row reveal in batting tables (stagger via Textual `set_interval`).
- Spinner-while-fetching transitions smoothly into the scorecard (cross-fade by mounting `ScorecardScreen` and unmounting `LoadingScreen` with a CSS transition).
- Sparkline for the worm/run-rate in `MatchHeader` (Rich `Bar` row from per-over runs if available).

**Acceptance:** Subjective — looks polished, animations don't block input. Manual smoke test on the example URL plus one Test match URL.

#### Phase 5 — Robustness

- Error screens: `InvalidUrlError`, `MatchNotFoundError`, `NetworkError` each render a styled error card with a hint and a `r` to retry.
- Disk cache: `~/.cache/cricscore/<match_id>.json` with a 60-second TTL; bypass via `--no-cache`.
- Logging to `~/.cache/cricscore/cricscore.log` (Rich handler) behind `--debug`.
- CI: GitHub Actions workflow running `ruff`, `mypy`, `pytest` on push.

#### Phase 6 — Stretch

- Live auto-refresh (30s poll while match status is `in_progress`).
- Commentary tab (separate API endpoint).
- Series view: paste a series URL → list matches → pick one.
- Player drill-down: click a batter → career-stats card via `hs-consumer-api`.
- Package to PyPI as `cricscore`.

### Risks and mitigations

| Risk                                                       | Mitigation                                                                                                                                              |
| ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `curl_cffi` impersonation eventually broken by Akamai      | Pin a known-good `impersonate` profile; document a Playwright-headless fallback path; the API surface (`ESPNCricinfoClient.fetch_scorecard`) is stable. |
| ESPNCricinfo JSON shape varies between formats (T20 / Test) | Pydantic models use `Optional[...]` for format-specific fields; fixture-driven tests cover both an IPL match and one Test match before Phase 4 ships.   |
| Textual API churn between minor versions                   | Pin `textual>=0.80,<1.0` in `pyproject.toml`; revisit when Textual 1.0 ships.                                                                           |
| User runs an old Python                                    | `requires-python = ">=3.12"` + clear README note.                                                                                                       |

### Critical files to create (Phase 1 only — what the first commit contains)

- `/Users/himzter/Documents/Programming/Projects/CricScore/pyproject.toml`
- `/Users/himzter/Documents/Programming/Projects/CricScore/README.md`
- `/Users/himzter/Documents/Programming/Projects/CricScore/PLAN.md` (copy of this document)
- `/Users/himzter/Documents/Programming/Projects/CricScore/.gitignore`
- `/Users/himzter/Documents/Programming/Projects/CricScore/.python-version`
- `/Users/himzter/Documents/Programming/Projects/CricScore/src/cricscore/__init__.py`
- `/Users/himzter/Documents/Programming/Projects/CricScore/src/cricscore/__main__.py`
- `/Users/himzter/Documents/Programming/Projects/CricScore/src/cricscore/cli.py`
- `/Users/himzter/Documents/Programming/Projects/CricScore/src/cricscore/url_parser.py`
- `/Users/himzter/Documents/Programming/Projects/CricScore/tests/__init__.py`
- `/Users/himzter/Documents/Programming/Projects/CricScore/tests/test_url_parser.py`

### Git workflow for the first push

The repo `himzterr/CricScore` is already created on GitHub and currently empty.

1. `git init -b main` in the project root.
2. Stage the Phase 1 files above.
3. Commit: `chore: initial scaffold + multi-phase plan`.
4. `git remote add origin https://github.com/himzterr/CricScore.git`.
5. `git push -u origin main`.

(All git work is held until plan approval — plan mode currently blocks writes.)

## Verification

After Phase 1 lands and dependencies are installed:

```bash
cd /Users/himzter/Documents/Programming/Projects/CricScore
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 1. URL parser smoke test
cricscore "https://www.espncricinfo.com/series/ipl-2026-1510719/kolkata-knight-riders-vs-delhi-capitals-70th-match-1529313/full-scorecard"
# expected: MatchRef(series_id=1510719, match_id=1529313)

# 2. Invalid URL
cricscore "https://example.com/foo"
# expected: non-zero exit, friendly "not a recognized ESPNCricinfo scorecard URL" message

# 3. Tests
pytest -q
# expected: all green
```

End-to-end verification after Phase 3:

- Run `cricscore "<the IPL match URL>"` and confirm: header shows teams + result, both innings render with batting + bowling tables matching the live scorecard, `q` quits cleanly, no tracebacks.
- Resize the terminal — layout reflows without clipping.
- Re-run with the network disconnected — error screen appears, not a stack trace.
