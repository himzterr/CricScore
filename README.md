# CricScore

A polished terminal UI for ESPNCricinfo match scorecards. Paste a full-scorecard
URL, watch the match render in your terminal with animated text effects.

> Status: **Phase 4 — polished TUI.** Typewriter title, gradient scores,
> per-over runs sparkline, staggered batting-table reveal, cycling
> loading-screen status. Robustness (error screens + cache) lands in
> Phase 5. See [PLAN.md](./PLAN.md) for the full roadmap.

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

```bash
# Launch the TUI (default)
cricscore "https://www.espncricinfo.com/series/ipl-2026-1510719/kolkata-knight-riders-vs-delhi-capitals-70th-match-1529313/full-scorecard"

# Or open the in-app URL paste screen
cricscore

# Non-interactive: human-readable summary
cricscore --summary "<url>"

# Non-interactive: full structured data
cricscore --json "<url>" | jq .
```

### Key bindings (TUI)

| Key   | Action                  |
| ----- | ----------------------- |
| `n`   | Next innings tab        |
| `p`   | Previous innings tab    |
| `tab` | Cycle focus             |
| `q`   | Quit                    |

## Development

```bash
pytest -q          # run tests
ruff check .       # lint
mypy src           # type-check
```

## Roadmap

See [PLAN.md](./PLAN.md) for the full multi-phase plan. In short:

1. **Phase 1** — Scaffolding + URL parser ✅
2. **Phase 2** — Data layer (curl_cffi + HTML `__NEXT_DATA__` + pydantic models) ✅
3. **Phase 3** — TUI skeleton (header, batting & bowling tables, fall of wickets) ✅
4. **Phase 4** — Text effects & polish (typewriter, gradients, sparkline, animated reveals) ✅
5. **Phase 5** — Robustness (error screens, disk cache, CI) ← *next*
4. **Phase 4** — Text effects & polish (typewriter, gradients, animated reveals)
5. **Phase 5** — Robustness (error screens, disk cache, CI)
6. **Phase 6** — Stretch (live refresh, commentary, series view, player drill-down)

## License

MIT
