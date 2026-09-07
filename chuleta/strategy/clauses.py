"""Buyout-clause intelligence, both directions.

Defense: which of MY players become cheap clause targets once their protection
expires. Offense: which rival players are (or will be) worth paying the clause
for. The key metric is the clause/value ratio PROJECTED at unlock time: a fixed
clause over a rising value is how people get sniped.
"""

from datetime import datetime, timezone

from ..matching import POS
from .values import curve as api_rate

RISK_RATIO = 1.5   # my player is at risk below this projected ratio
PREY_RATIO = 1.4   # a rival player is worth hunting below this


def _days_locked(iso, now):
    if not iso:
        return 0
    try:
        return max(0, (datetime.fromisoformat(iso) - now).days)
    except ValueError:
        return 0


def _row(player, client, now):
    pm = player["playerMaster"]
    clause = player.get("buyoutClause")
    if not clause:
        return None
    data = api_rate(client, pm["id"])
    value = data[0] if data else int(pm.get("marketValue") or 0)
    rate = data[1] if data else 0.0
    days = _days_locked(player.get("buyoutClauseLockedEndTime"), now)
    projected_value = max(1, value + rate * days)
    # While locked the clause floors at market value, so at opening it is
    # never below the projected value: a ratio of 1.0 means "anyone can pay value".
    return {
        "nombre": pm.get("nickname") or pm.get("name"),
        "player_id": pm["id"],
        "pos": POS.get(int(pm.get("positionId") or 0), "?"),
        "valor": value,
        "clausula": clause,
        "rate": round(rate),
        "dias_protegido": days,
        "ratio_hoy": round(clause / max(value, 1), 2),
        "ratio_al_abrir": round(max(clause, projected_value) / projected_value, 2),
    }


def analyze(client, league_id, my_team_id):
    """{'mine': [...], 'rivals': [...]}, each sorted most-exposed first."""
    now = datetime.now(timezone.utc)
    mine, rivals = [], []
    for s in client.standings(league_id):
        tid = str(s["team"]["id"])
        manager = s["team"]["manager"]["managerName"]
        team = client.team(league_id, tid)
        for p in team.get("players", []):
            row = _row(p, client, now)
            if not row:
                continue
            row["manager"] = manager
            (mine if tid == str(my_team_id) else rivals).append(row)
    mine.sort(key=lambda r: r["ratio_al_abrir"])
    rivals.sort(key=lambda r: r["ratio_al_abrir"])
    return {"mine": mine, "rivals": rivals}
