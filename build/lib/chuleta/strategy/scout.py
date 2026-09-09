"""Market screening: the four-leg buy filter with hard vetoes.

Legs: (1) value trend on the API's real history, (2) minutes and games this
season, (3) press starting odds, (4) historic points. Vetoes: any status but
ok; falling >= 0.5%/day; falling with zero games (a transfer in progress);
low odds with low average; listed by the press without odds while fit (a
player forced out of the XI); a transfer, injury or conflict headline.
"""

from ..api import club_of
from ..matching import POS, match_name
from ..sources.clubs import club_names
from ..sources.last_season import last_season_points
from ..sources.news import bad_news_for
from ..sources.press import club_slug, club_slugs, probable_lineups
from . import values

FALLING_PCT_VETO = -0.5


def _season_usage(client, player_id):
    detail = client.player(player_id)
    stats = detail.get("playerStats") or []
    minutes = sum(((s.get("stats") or {}).get("mins_played") or [0])[0] or 0 for s in stats)
    return len(stats), minutes, detail.get("averagePoints"), detail.get("lastSeasonPoints"), detail


def _entry_price(el, value):
    pt = el.get("playerTeam") or {}
    if el.get("discr") == "marketPlayerLeague" or not pt:
        return max(el.get("salePrice") or 0, value), "SISTEMA"
    return pt.get("buyoutClause") or max(el.get("salePrice") or 0, value), "CLAUSULA"


def study(client, league_id, horizon=7):
    press = probable_lineups()
    slugs = club_slugs()
    clubs = club_names(client)
    rows = []
    for el in client.market(league_id):
        pm = el.get("playerMaster") or {}
        if not pm.get("id"):
            continue
        c = values.curve(client, pm["id"])
        value, rate = c if c else (int(pm.get("marketValue") or 0), 0.0)
        games, minutes, avg, last_detail, detail = _season_usage(client, pm["id"])
        info = match_name(pm.get("nickname", ""), pm.get("name", ""), press)
        prob = info.get("prob") if info else None
        press_dropped = bool(info) and prob is None and not info.get("lesionado") and info.get("disponible", True)
        club = club_of(detail if detail.get("team") else pm, clubs)[0]
        slug = (info or {}).get("equipo") or club_slug(club, slugs)
        news = []
        if slug:
            try:
                news = bad_news_for(pm.get("nickname", ""), pm.get("name", ""), slug)
            except Exception:
                news = []
        status = pm.get("playerStatus")
        rate_pct = rate / value * 100 if value else 0.0
        entry, via = _entry_price(el, value)
        _, margin_pct = values.margin(entry, value, rate, horizon) if entry else (0, None)

        vetoes = []
        if status != "ok":
            vetoes.append(f"estado {status}")
        if rate_pct <= FALLING_PCT_VETO:
            vetoes.append("cayendo fuerte")
        if rate < 0 and games == 0:
            vetoes.append("cae sin haber jugado (¿traspaso?)")
        if prob is not None and prob < 40 and (avg or 0) < 3:
            vetoes.append(f"titularidad {prob}%")
        if press_dropped:
            vetoes.append("descartado por la prensa sin lesión (¿conflicto/salida?)")
        for n in news[:2]:
            vetoes.append(f"noticia {n['fecha']}: {n['titular'][:70]}")

        hist = pm.get("lastSeasonPoints")
        if hist is None:
            hist = last_detail if last_detail is not None else last_season_points(pm.get("nickname", ""), pm.get("name", ""))
        pt = el.get("playerTeam") or {}
        rows.append({
            "nombre": pm.get("nickname") or pm.get("name"), "pos": POS.get(int(pm.get("positionId") or 0), "?"),
            "equipo": club, "vendedor": (pt.get("manager") or {}).get("managerName", "SISTEMA") if pt else "SISTEMA",
            "via": via, "entrada": entry, "valor": value, "tend_dia": round(rate), "margen_pct": margin_pct,
            "ptos_25_26": hist, "pj": games, "minutos": minutes, "media": float(avg or 0), "prob": prob,
            "estado": status, "vetos": vetoes, "market_id": el.get("id"), "pujas": el.get("numberOfBids", 0),
        })
    rows.sort(key=lambda r: (bool(r["vetos"]), -(r["margen_pct"] if r["margen_pct"] is not None else -99)))
    return rows
