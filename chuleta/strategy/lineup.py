"""Best XI by expected points.

expected = P(plays) x points per game x fixture factor

P(plays): press odds when available; a player who played 60+ minutes last
week counts as a likely starter even if the press page (which lags a day)
omits him; otherwise a guess from market value. Doubtful players are
discounted; injured and suspended ones never fielded.

Points per game: this season's average blended with last season's per-game
figure while the sample is short (full weight at 4 games).

Fixture factor: opponent and own goal difference per game plus home advantage,
at a QUARTER of the effect measured over three seasons. The cross-team backtest
in research/ shows the full effect over-boosts middling players with soft
fixtures and drops stars with hard ones; recent form loses to the long average.
"""

from ..matching import match_name
from ..sources.form import goal_diff_per_game, team_form
from ..sources.press import probable_lineups

FORMATIONS = [(3, 4, 3), (3, 5, 2), (4, 3, 3), (4, 4, 2), (4, 5, 1), (5, 3, 2), (5, 4, 1)]
LINE = {1: "goalkeeper", 2: "defender", 3: "midfield", 4: "striker"}
OUT = ("injured", "suspended", "out_of_league")
DOUBTFUL = ("doubtful", "duda", "warned")
DOUBTFUL_DISCOUNT = 0.6
BENCHED_PROB = 0.05
PLAYED_LAST_PROB = 0.6
LAST_SEASON_GAMES = 34
OPP_WEIGHT = {1: 0.06, 2: 0.06, 3: 0.045, 4: 0.045}
OWN_WEIGHT = 0.055
HOME_BONUS = 0.035


def prob_from_value(value):
    """Starting odds guessed from price when the press says nothing."""
    v = int(value or 0)
    for floor, prob in ((30e6, .82), (15e6, .62), (8e6, .52), (4e6, .42), (2e6, .28)):
        if v >= floor:
            return prob
    return .12


def points_per_game(pm, last_season=None, history=None):
    """This season's average, blended with points/game from prior seasons
    while the sample is short (full weight at 4 games). `history` (optional)
    is `season_points.historical_per_game`: a 3-season weighted blend, tried
    first since it beats a single season; `last_season` (the legacy single-
    season lookup) is the fallback for a player absent from all 3 — e.g. a
    summer arrival from outside LaLiga."""
    avg = float(pm.get("averagePoints") or 0)
    pts = float(pm.get("points") or 0)
    games = round(pts / avg) if avg else 0

    hist_pg = history(pm.get("nickname", ""), pm.get("name", "")) if history else None
    if hist_pg is None:
        last = pm.get("lastSeasonPoints")
        if last is None and last_season is not None:
            last = last_season(pm.get("nickname", ""), pm.get("name", ""))
        hist_pg = (int(last) / LAST_SEASON_GAMES) if last not in (None, "", 0) else None

    if not avg and hist_pg is None:
        return prob_from_value(pm.get("marketValue")) * 10
    if hist_pg is None:
        return avg
    w = min(games, 4) / 4
    return w * avg + (1 - w) * hist_pg


def fixture_factor(pm, form):
    if not form:
        return 1.0
    tid = str((pm.get("team") or {}).get("id") or pm.get("teamId") or "")
    nxt = (form.get("next") or {}).get(tid)
    if not nxt:
        return 1.0
    opp = goal_diff_per_game(form["form"], nxt["opp"])
    own = goal_diff_per_game(form["form"], tid)
    w = OPP_WEIGHT.get(int(pm.get("positionId") or 0), 0.045)
    f = (1 - w * opp) * (1 + OWN_WEIGHT * own) * (1 + HOME_BONUS if nxt["home"] else 1 - HOME_BONUS)
    return max(0.4, min(1.8, f))


def score_player(player, press, form=None, recent_minutes=None, last_season=None, history=None):
    """(expected points, P(plays) as %, available, tag)."""
    pm = player["playerMaster"]
    info = match_name(pm.get("nickname", ""), pm.get("name", ""), press)
    status = (pm.get("playerStatus") or "ok").lower()
    if status in OUT or (info and (info.get("lesionado") or not info.get("disponible", True))):
        return 0.0, 0, False, "baja"
    prob = info.get("prob") if info else None
    if info is None:
        p, tag = prob_from_value(pm.get("marketValue")), "sin prensa"
    elif prob is not None:
        p, tag = prob / 100, "prensa"
    else:
        p, tag = BENCHED_PROB, "fuera del once"
    mins = (recent_minutes or {}).get(player.get("playerTeamId"), 0)
    if tag != "prensa" and mins >= 60:
        p, tag = max(p, PLAYED_LAST_PROB), "jugó la última"
    if status in DOUBTFUL:
        p, tag = p * DOUBTFUL_DISCOUNT, "duda"
    exp = p * points_per_game(pm, last_season, history) * fixture_factor(pm, form)
    return exp, round(p * 100), True, tag


def _pick(entries, n):
    """Best n available entries of a line; fills with unavailable ones only
    when the line is short, so the XI is always complete and position-legal."""
    ok = sorted((e for e in entries if e["disponible"]), key=lambda e: -e["score"])
    ko = sorted((e for e in entries if not e["disponible"]), key=lambda e: -e["score"])
    chosen = (ok + ko)[:n]
    return chosen if len(chosen) == n else None


def optimize(team, press=None, form=None, recent_minutes=None, last_season=None, history=None):
    """Best formation and XI. Returns a dict with lines, total and the payload
    for Client.save_lineup, or raises ValueError if no legal XI exists."""
    if press is None:
        press = probable_lineups()
        if form is None:
            try:
                form = team_form()
            except Exception:
                form = None
    lines = {1: [], 2: [], 3: [], 4: []}
    for p in team.get("players", []):
        pos = int(p["playerMaster"].get("positionId") or 0)
        if pos not in lines:
            continue
        exp, prob, ok, tag = score_player(p, press, form, recent_minutes, last_season, history)
        lines[pos].append({"id": p.get("playerTeamId"), "nombre": p["playerMaster"].get("nickname"),
                           "score": round(exp, 2), "prob": prob, "disponible": ok, "tag": tag})
    gk = _pick(lines[1], 1)
    if not gk:
        raise ValueError("no goalkeeper in the squad")
    best = None
    for d, m, f in FORMATIONS:
        picked = [_pick(lines[2], d), _pick(lines[3], m), _pick(lines[4], f)]
        if any(x is None for x in picked):
            continue
        total = gk[0]["score"] + sum(e["score"] for line in picked for e in line)
        if best is None or total > best["total"]:
            best = {"formation": (d, m, f), "total": round(total, 1), "goalkeeper": gk[0],
                    "defender": picked[0], "midfield": picked[1], "striker": picked[2]}
    if best is None:
        raise ValueError("fewer than 11 fieldable players")
    chosen = {best["goalkeeper"]["id"]} | {e["id"] for k in ("defender", "midfield", "striker") for e in best[k]}
    best["bench"] = [e["nombre"] for line in lines.values() for e in line if e["id"] not in chosen]
    return best


def recent_minutes(client, team):
    """playerTeamId -> minutes in the latest gameweek with stats."""
    out = {}
    for p in team.get("players", []):
        try:
            weeks = [w for w in (client.player(p["playerMaster"]["id"]).get("playerStats") or []) if w.get("weekNumber")]
            if weeks:
                last = max(weeks, key=lambda w: w["weekNumber"])
                out[p.get("playerTeamId")] = int(((last.get("stats") or {}).get("mins_played") or [0])[0] or 0)
        except Exception:
            continue
    return out
