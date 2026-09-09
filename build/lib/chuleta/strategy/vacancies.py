"""Who inherits a starting spot when a teammate is out.

For every club: players out (injured / doubtful / suspended per the API, or
flagged by the press) ranked by what they were scoring, and the same-position
teammates who can take the minutes, ranked by press odds, last week's minutes
and historic points. The Zabiri (Andrés Martín out) and Mariano (Toni Martínez
out) buys were exactly this pattern, found by hand.
"""

from ..matching import POS, match_name, normalize
from ..sources.press import probable_lineups
from ..sources.last_season import last_season_points
from ..sources.clubs import club_names

OUT = ("injured", "doubtful", "suspended", "out_of_league")


def _press(pm, idx):
    info = match_name(pm.get("nickname", ""), pm.get("name", ""), idx)
    return info or {}


def study(client, league_id, club_filter=None, min_points=10):
    clubs = club_names(client)
    idx = probable_lineups()
    players = client.players()
    listed = {e["playerMaster"]["id"]: e for e in client.market(league_id)}
    by_club = {}
    for p in players:
        by_club.setdefault(str(p.get("teamId")), []).append(p)
    out = []
    for tid, roster in by_club.items():
        club = clubs.get(tid, f"?{tid}")
        if club_filter and normalize(club_filter) not in normalize(club):
            continue
        for p in roster:
            info = _press(p, idx)
            status = p.get("playerStatus") or "ok"
            pressed_out = bool(info) and (info.get("lesionado") or not info.get("disponible", True))
            if status not in OUT and not pressed_out:
                continue
            pts = p.get("points") or 0
            hist = p.get("lastSeasonPoints")
            hist = int(hist) if hist not in (None, "0", 0) else last_season_points(p.get("nickname", ""), p.get("name", ""))
            if pts < min_points and (hist or 0) < 60:
                continue  # a bench body being out frees no minutes worth chasing
            pos = str(p.get("positionId"))
            heirs = []
            for q in roster:
                if q is p or str(q.get("positionId")) != pos or (q.get("playerStatus") or "ok") in OUT:
                    continue
                qi = _press(q, idx)
                if qi and (qi.get("lesionado") or not qi.get("disponible", True)):
                    continue
                qh = q.get("lastSeasonPoints")
                qh = int(qh) if qh not in (None, "0", 0) else (last_season_points(q.get("nickname", ""), q.get("name", "")) or 0)
                heirs.append({
                    "nombre": q.get("nickname"), "valor": int(q.get("marketValue") or 0),
                    "prob": qi.get("prob") if qi else None, "media": float(q.get("averagePoints") or 0),
                    "ptos": q.get("points") or 0, "ptos_25_26": qh,
                    "mercado": listed.get(q["id"]),
                })
            heirs.sort(key=lambda h: (-(h["prob"] or 0), -h["media"], -h["ptos_25_26"]))
            out.append({
                "equipo": club, "baja": p.get("nickname"), "pos": POS.get(int(pos), "?"),
                "estado": status if status in OUT else "descartado por la prensa",
                "media": float(p.get("averagePoints") or 0), "ptos": pts, "ptos_25_26": hist,
                "herederos": heirs[:4],
            })
    out.sort(key=lambda r: -(r["media"] * 3 + (r["ptos_25_26"] or 0) / 34))
    return out
