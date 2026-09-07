# Chuleta

A trading desk for the official **LALIGA Fantasy** game, from the command line.
It reads the game's (unofficial) API and futbolfantasy.com and tells you, in
Spanish and with the data on the table, what to buy, what to sell, who to line
up and how much cash your rivals really have.

Standard library only. Python 3.11+. MIT.

## What it does

| Command | What you get |
|---|---|
| `chuleta mercado` | Every player on the market with a four-leg buy filter (value trend on the API's real history, minutes and games, press starting odds, historic points) and hard vetoes: injured or suspended, falling hard, falling with zero minutes (a transfer in progress), press-dropped while fit, transfer or conflict headlines. |
| `chuleta alinear [--aplicar]` | Best XI and formation by **expected points**: P(plays) x points per game x a fixture factor calibrated on three full seasons (see `research/`). Players who played 60+ minutes last week count as starters even when the press page lags. |
| `chuleta bajas [club]` | Injured or suspended starters per club and the same-position teammates set to inherit their minutes, with their press odds and whether they are on the market. |
| `chuleta caja` | Every manager's estimated cash, rebuilt from the public activity feed. |
| `chuleta clausulas` | Your clause exposure and rivals' clause targets, with days until each unlocks. |
| `chuleta trading` | Ledger: open positions with P&L, realised sales, your listings and today's machine offers. |
| `chuleta historial <name>` | Value curve day by day and points per matchday. |
| `chuleta onces <club>` / `chuleta noticias <club>` | The press's probable XI and typed headlines (injury, transfer, unavailable). |
| `chuleta listar <name> <price>` / `retirar` / `acepta --si` / `puja <marketId>` | Act. Accepting an offer is irreversible and asks you to confirm with `--si`. |

## Quick start

```bash
pip install .
chuleta login                       # prints a URL; sign in with your Google account
chuleta login "authredirect://..."  # paste the URL the browser fails to open
chuleta ligas
chuleta mercado
chuleta alinear
```

Session and cache live in `~/.chuleta` (override with `CHULETA_HOME`). With
several leagues, pin one with `CHULETA_LEAGUE=<id>`.

## Game mechanics the tool relies on

Values update daily at 00:15 (Madrid); auctions resolve at 15:24. A bid must be
at least the player's current value. The machine offers 90-110% of value on
every listing each cycle, whatever you ask. The XI saved before the first match
of a gameweek scores for the whole gameweek. A clause floors at market value
while locked; raising it costs 50% of the increment. The maximum bid is cash
plus 20% of your squad's value, and a negative balance at kick-off scores zero.

## What the data says

`research/` holds the scrapers and the findings from three seasons of
per-player, per-match points (2023/24 to 2025/26): a win is worth 7.1 points
per starter, a draw 5.1, a loss 2.8; the opponent's goal difference costs ~22%
per goal; and a cross-team backtest shows the plain long-run average picks a
better XI than a full fixture adjustment, which is why the lineup model weighs
fixtures at a quarter of their measured effect. The raw scraped data is not
redistributed; the scrapers are.

## Acknowledgements

The idea of driving LALIGA Fantasy from a CLI, and the map of its login and
endpoints, were first explored in [jonortega20/fantasybot](https://github.com/jonortega20/fantasybot).
Chuleta is an independent implementation.
