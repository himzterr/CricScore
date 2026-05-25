# CricScore

A polished terminal UI for ESPNCricinfo match scorecards. Paste a full-scorecard
URL, watch the match render in your terminal with animated text effects.

> Status: **Phase 1 — scaffolding only.** The CLI parses URLs today; the
> scraper and TUI land in subsequent phases. See [PLAN.md](./PLAN.md) for the
> full roadmap.

## Requirements

- Python **3.12+**
- A terminal that supports 256 colors / truecolor (any modern terminal works)

## Install

```bash
git clone https://github.com/himzterr/CricScore.git
cd CricScore
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Usage

Today (Phase 1) the CLI just parses a URL and prints the resolved match
identifiers:

```bash
cricscore "https://www.espncricinfo.com/series/ipl-2026-1510719/kolkata-knight-riders-vs-delhi-capitals-70th-match-1529313/full-scorecard"
# → MatchRef(series_id=1510719, match_id=1529313)
```

After Phase 3 the same command will open the TUI and render the full
scorecard.

## Development

```bash
pytest -q          # run tests
ruff check .       # lint
mypy src           # type-check
```

## Roadmap

See [PLAN.md](./PLAN.md) for the full multi-phase plan. In short:

1. **Phase 1** — Scaffolding + URL parser ← *current*
2. **Phase 2** — Data layer (curl_cffi + ESPNCricinfo JSON API + pydantic models)
3. **Phase 3** — TUI skeleton (header, batting & bowling tables, fall of wickets)
4. **Phase 4** — Text effects & polish (typewriter, gradients, animated reveals)
5. **Phase 5** — Robustness (error screens, disk cache, CI)
6. **Phase 6** — Stretch (live refresh, commentary, series view, player drill-down)

## License

MIT
