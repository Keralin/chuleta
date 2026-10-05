# Working on chuleta

The README covers what the tool does and how to run it. This file covers what
the code will not tell you on its own: how a release is cut, and the places
where the upstream data lies.

## Shape of the code

```
chuleta/api.py          every HTTP call to the LALIGA Fantasy API, nothing else
chuleta/auth.py         OAuth2 through Azure B2C, two-step `chuleta login`
chuleta/config.py       endpoints, ids and paths. No secrets
chuleta/matching.py     name matching between the API and the press
chuleta/sources/        outside data: press lineups, news, club names, past seasons
chuleta/strategy/       the thinking: scout, values, trend, clauses, lineup,
                        cash, sniper, schedule, vacancies
chuleta/cli.py          argparse, the printing, Spanish output
```

Pure stdlib, no dependencies, and worth keeping that way: it is meant to run
wherever a bare `python3` is, including boxes with no `pip` at all, so anything
that needs installing cannot run where the bot does.

Reports print in Spanish, code and commits are in English.

## State lives outside the repo

`~/.chuleta/` holds `tokens.json`, `pkce.json`, `cache/` and `state/` (the
sniper plan). Overridable with `CHULETA_HOME`. Nothing stateful sits in the
working tree.

`tokens.json` is a credential. Never cat, grep or echo it: a token that reaches
a terminal transcript is burned and `chuleta login` has to run again.

`sniper ejecutar` places real bids and `acepta` sells for real. Everything else
only reads.

## Releases

`release-please` watches `main` and keeps a release pull request open,
regenerating it on every merge. So:

- Merge everything else first, the release pull request **last**, or the
  version gets cut without the work that is still queued.
- **Squash merge.** A merge commit makes release-please count the change twice
  and the entry lands in the changelog twice. 0.2.0 shipped with four such
  duplicates removed by hand.
- A commit whose prefix is not a conventional type is invisible to the
  changelog. `values: price the exit...` had to be added by hand.
- `include-component-in-tag` is off on purpose: with it on, naming the package
  makes the tag `chuleta-v0.2.0` and the previous `v0.1.0` stops being found as
  the baseline, which drags already released commits into the notes.

The `python` release type updates `pyproject.toml` and `chuleta/__init__.py` by
itself, reading the package directory from the project name. No `extra-files`.

CI runs the suite on 3.11, the floor in `pyproject.toml`, and 3.14. Use
`pip install -e '.[dev]'` for a checkout you can test in.

## Where the upstream data lies

Each of these produced a wrong call before it was handled. They are the reason
the strategy modules look more defensive than the API would suggest.

**The value history lands a day late.** `value_history` stops at yesterday for
part of a squad while `marketValue` on the player payload is already today. Read
the value off the history alone and today's move reads as yesterday's, and the
streak, the acceleration and the sort order all shift with it. `trend.summary`
and `values.curve` take a `live` value for this; pass it.

**`playerStatus` lags a real injury.** It kept saying `ok` for a player whose
club had already announced him as training apart. Cross-check the press.

**The press injury tag is sticky, and the starting odds do not rescue it.** The
tag stays on a player long after he is fit: five players of one club carried it
at once. Pairing it with the odds looks like a fix and is not, because the odds
do not separate the cases: one player carried the tag at 80% while his club had
ruled him out, another carried it at 70% and started. `press.condition()`
returns `out`, `doubt` or `fit` for this, and only the API status or a
suspension makes an absence.

**`mercado`'s daily trend is a seven day average.** A player who turned three
days ago can still show a positive trend and a buy verdict, and the same number
drives the falling-value veto, so that safety net goes quiet at the same moment.
Check the streak and the acceleration from `trend` before believing it.

**There is no global market close time.** Auctions resolve at the hour the
league was created, so every league rotates at a different minute and nothing
should hardcode one. `sniper.cycle_utc()` reads it from the `expirationDate` of
the league's own listings and `sniper.cron_line()` builds the cron entry from
that, which is why `chuleta sniper cron` exists instead of a constant.

**The activity feed is paged newest first, from page 0.** Types: `31` bought
from the system, `33` sold to the system, `1` a transfer between managers where
`user1Id` is the buyer and `user2Id` the seller, `6` the weekly prize. Clause
raises never appear, so a cash estimate rebuilt from the feed is a ceiling, not
a figure.

**Clause windows need hours, not days.** Truncating
`buyoutClauseLockedEndTime` to whole days makes a clause that opens tonight read
the same as one already open.

**Far-off gameweeks have no real kickoff times.** The calendar answers with the
same placeholder hour for all ten matches until they are set.
`schedule.scheduled()` detects it. `current_week().openingWeekDate` is the
freeze for the current one.

**League and market ids are `playerTeamId`, not `playerId`.** And the API does
not answer from GitHub Actions runners, so nothing that calls it can live in CI.

## Known issues

Symptom first, then the fix. Add, never delete.

- **`pytest` may not be installable** where the bot runs, since there is no
  `pip` on a bare-python box. Run the suite in CI, or drive the test functions
  from a stdlib runner for a quick local check.
- **`mercado` says buy about a player whose value turned days ago**, because the
  trend it prints is a seven day average. See above.
