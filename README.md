# CricScore

A polished terminal UI for ESPNCricinfo match scorecards. Paste a full-scorecard
URL, watch the match render in your terminal with animated text effects.

> Status: **Phase 2 — data layer working.** The CLI scrapes ESPNCricinfo
> (via curl_cffi + HTML `__NEXT_DATA__`) and returns a typed `Match` model.
> The Textual UI lands in Phase 3. See [PLAN.md](./PLAN.md) for the full
> roadmap.

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
# Human-readable summary
cricscore "https://www.espncricinfo.com/series/ipl-2026-1510719/kolkata-knight-riders-vs-delhi-capitals-70th-match-1529313/full-scorecard"
# 70th Match — Eden Gardens, Kolkata
#   DC won by 40 runs
#   Delhi Capitals: 203/5
#   Kolkata Knight Riders: 163  (18.4/20 ov, T:204)
#     DC 203/5 in 20.0 overs (batters 11, fow 5)
#     KKR 163/10 in 18.4 overs (batters 11, fow 10)

# Full structured data
cricscore --json "<url>" | jq .
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

1. **Phase 1** — Scaffolding + URL parser ✅
2. **Phase 2** — Data layer (curl_cffi + HTML `__NEXT_DATA__` + pydantic models) ✅
3. **Phase 3** — TUI skeleton (header, batting & bowling tables, fall of wickets) ← *next*
4. **Phase 4** — Text effects & polish (typewriter, gradients, animated reveals)
5. **Phase 5** — Robustness (error screens, disk cache, CI)
6. **Phase 6** — Stretch (live refresh, commentary, series view, player drill-down)

## License

MIT
