# Research: what actually predicts LaLiga Fantasy points

Data scraped from futbolfantasy match pages ("Puntuaciones" table, first
column = LaLiga Fantasy Oficial points), one JSON per season:

| file | season | matches |
|---|---|---|
| data/matches_2324.json | 2023/24 | 380 |
| data/matches_2425.json | 2024/25 | 380 |
| data/matches_2526.json | 2025/26 | 380 |
| data/comps.json | Champions, Europa League, Copa (dates, teams, scores) | 846 |

Each match: `teams`, `score`, `date` (Spanish month names), `players`
(`side`, `name`, `mins`, `starter`, `pts`). The site keys seasons by the
closing year: `/laliga/calendario/2026` is 2025/26.

## Findings (drive `chuleta/strategy/lineup.py`)

- Per starter (60+ min): win 7.1 pts, draw 5.1, loss 2.8. Home 5.3 vs away 4.6.
- Each goal of the opponent's goal difference per game costs ~22% (GK/DEF
  more, MED/DEL less); each goal of own goal difference adds ~24%.
- Upsets pay like ordinary wins (6.9 vs 7.1); they are just rare.
- Cross-team backtest (pick the best XI of each round among ~190 starters,
  training only on earlier data): test 24/25 plain average 88.5 pts vs full
  fixture factor 85.6 vs quarter factor 87.1; test 25/26 plain 85.3 vs full
  89.8 vs quarter 89.8. Quarter-weight fixture factor is what ships.
- Recent form (last 8 games) loses to the long-run average (80.8 vs 88.5).
- A midweek European/Copa match in the previous 2-5 days: -0.2 pts per
  starter (-4%), not modelled.

## Scripts

- `scripts/ff_match.py` parse one match page.
- `scripts/scrape_season.py <end-year> <out.json>` scrape a LaLiga season.
- `scripts/scrape_comps.py` dates of cup and European matches.
- `scripts/backtest.py` the cross-team XI backtest.

The raw JSON is derived from a third-party site: keep it private, publish
only aggregates.
