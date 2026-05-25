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

#### Phase 2 — Data layer ✅ shipped

Empirical reality at fetch time (May 2026): the `hs-consumer-api.espncricinfo.com` JSON endpoint is Akamai-gated past what `curl_cffi` Chrome impersonation can defeat — it returns 403 with every profile we tried (`chrome120/124/131`, `safari17_*`, `edge99/101`, `firefox135`) even with warmed cookies and a real `Referer`. The HTML pages however return 200 and embed the **full** match payload in a `__NEXT_DATA__` script tag (~970 KB per scorecard), which is what the data layer now scrapes.

- `src/cricscore/_native.py` — Pattern 1 hook: tries `cricscore._native_rs`, falls back to Python. Future Rust acceleration drops in via `maturin develop` with zero caller changes.
- `src/cricscore/api/_python_client.py` — curl_cffi session that warms cookies on the homepage then loads `/series/x-<series_id>/y-<match_id>/full-scorecard` (placeholder slugs — ESPN redirects). Extracts `props.appPageProps.data` from `__NEXT_DATA__`.
- `src/cricscore/api/client.py` — `ESPNCricinfoClient.fetch_scorecard(MatchRef) -> dict`, dispatching through `_native`.
- `src/cricscore/api/endpoints.py` — HTML page URL builders.
- `src/cricscore/models/match.py` — pydantic models (`Match`, `Innings`, `Batter`, `Bowler`, `FallOfWicket`, `TeamScore`, `Ground`, `PlayerAward`) with `extra="ignore"` and aggressive optionality. `Match.from_scorecard_payload(dict)` is the public entry point.
- `tests/fixtures/scorecard_1529313.json` (1.6 MB) — captured live from the IPL match.
- `tests/test_models.py` — verifies metadata, team scores, batting lineup, top scorer (KL Rahul 60(30)), best bowler (Lungi Ngidi 3/27), Player of the Match (Kuldeep Yadav), and round-trip through JSON.
- `tests/test_extract_next_data.py` — covers the `__NEXT_DATA__` extractor against synthetic HTML.
- CLI: `cricscore <url>` prints a human summary; `cricscore <url> --json` prints the parsed `Match` as JSON.

**Acceptance:** `pytest -q` reports 27 passed; `cricscore <ipl-url>` prints "DC won by 40 runs" with both team scores and innings totals.

#### Phase 3 — TUI skeleton + scorecard render ✅ shipped

- `tui/app.py` (`CricScoreApp`): routes to `ScorecardScreen` if a `Match` is provided (tests), to `LoadingScreen` if a `MatchRef` is provided (CLI URL), or to `URLInputScreen` otherwise.
- `tui/screens/loading.py`: runs the curl_cffi fetch + pydantic parsing in a threaded Textual worker, then `switch_screen` to the scorecard. Error label shown if the fetch fails.
- `tui/screens/scorecard.py`: `MatchHeader` + `TabbedContent` over innings. Tab labels include team + score (`"DC 203/5"`, `"KKR 163/10"`). `n`/`p` cycle tabs; `q` quits.
- `tui/screens/url_input.py`: in-app URL paste — Input widget, validates with `parse_match_url`, switches to `LoadingScreen` on success.
- `tui/widgets/match_header.py`: title + format + status + venue + per-team score lines + PotM, all styled via Rich `Text` runs.
- `tui/widgets/batting_table.py`: `DataTable` with Batter / How out / R / B / 4s / 6s / SR; trailing rows for extras, total, and did-not-bat. 50+ scorers get a bold accent.
- `tui/widgets/bowling_table.py`: `DataTable` with O / M / R / W / Econ / WD / NB; 3-fer bowlers highlighted.
- `tui/widgets/fow_strip.py`: single-line fall-of-wickets summary, auto-hidden when empty.
- `tui/widgets/innings_panel.py`: `VerticalScroll` wrapping the three widgets above with section labels.
- `tui/styles.tcss`: deep-navy surface + warm-orange accent palette; custom vars are prefixed `$cs-` to avoid clobbering Textual's built-in tokens (we hit a real bug here — `$panel` is reserved).
- CLI: default action is TUI launch; `--summary` and `--json` retain the Phase 2 non-interactive paths; URL is optional (no-URL → URL input screen).
- `tests/test_tui_smoke.py`: 5 headless tests via `App.run_test` covering scorecard mount, tab count, batting-table rows, URL input fallback, and the `q` binding.

**Acceptance:** 32 tests passing. Headless render of the IPL match produces a `MatchHeader` for match id 125458, two innings tabs, 10 batting rows (7 batters + extras + total + DNB) and 6 bowling rows in the first innings, and `n` cycles tabs.

#### Phase 4 — Text effects & polish ✅ shipped

- `cricscore/effects/typewriter.py` — `TypewriterLabel` (Static subclass) reveals text character-by-character on a self-cancelling timer; `reset_to(text)` restarts with a new phrase.
- `cricscore/effects/gradient.py` — `gradient_text(text, start, end, *, bold)` returns a `rich.text.Text` with per-character RGB interpolation. Used on scores and totals.
- `cricscore/effects/sparkline.py` — `sparkline(values)` returns a row of Unicode block characters scaled to the input. Empty when all-zero / empty input so callers can hide the row cleanly.
- `models/match.py` — added `Innings.runs_per_over` and `Innings.wickets_per_over` exposing the ESPN `inningOvers` array. Sparkline reads from this; the model knows ESPN field names so widgets don't have to.
- `tui/widgets/match_header.py` — rebuilt as a `Vertical` container of small widgets: typewriter title, status, venue, gradient-coloured team scores, per-over runs sparkline (one per innings), PotM line.
- `tui/widgets/batting_table.py` — rows now stream in on a 35ms stagger via `set_interval`; first row appears synchronously so the table is never visibly empty; "Total" line uses the same warm gradient as scores.
- `tui/screens/loading.py` — typewriter status that cycles through ("Warming up the Akamai handshake...", "Fetching scorecard...", "Parsing innings...", "Rendering...") on a 0.9s rotation until the worker completes.
- `tests/test_effects.py` — 12 tests covering gradient endpoint colors, per-character spans, sparkline scaling, edge cases (empty, all-zero, None, negatives).

**Acceptance:** 45 tests passing. Headless snapshot grew from 75 KB → 98 KB (extra gradient spans + sparkline rows) and renders cleanly at 120×44.

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
