"""Typed club news from futbolfantasy team pages.

Each team page carries a news block where every item has a type icon
(traspaso, nodisponible, lesion...), a date and a headline naming the player.
That is the signal the market filter lacked when a manager tried to sell us a
player who was refusing to train to force a transfer: press had already
dropped him to no probability, and three headlines said why.
"""

import re
from datetime import datetime, timedelta

from .. import config, http
from ..matching import normalize

CACHE_TTL = 1800
RECENT_DAYS = 7
BAD_TYPES = {"traspaso", "nodisponible", "lesion", "sancion"}
BAD_WORDS = ("salida", "se niega", "niega a entrenar", "sancion", "lesion", "traspaso",
             "rescindir", "descartado", "baja", "fuera del equipo", "conflicto", "forzar")

_ITEM = re.compile(r'<a href="(https://www\.futbolfantasy\.com/laliga/noticias/[^"]+)" class="noticia">(.*?)</a>', re.S)


def _parse(html, slug):
    out = []
    year = datetime.now().year
    for href, body in _ITEM.findall(html):
        tipo = re.search(r'tiponoticia/icono_big_([a-z_]+)\.png', body)
        day = re.search(r'<span class="day">(\d\d)/(\d\d)</span>', body)
        tit = re.search(r'<h2[^>]*>(.*?)</h2>', body, re.S)
        if not tit:
            continue
        titular = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", tit.group(1))).strip()
        fecha = None
        if day:
            try:
                fecha = datetime(year, int(day.group(2)), int(day.group(1)))
                if fecha > datetime.now() + timedelta(days=1):  # December items seen in January
                    fecha = fecha.replace(year=year - 1)
            except ValueError:
                fecha = None
        out.append({"equipo": slug, "tipo": tipo.group(1) if tipo else "general",
                    "fecha": fecha.date().isoformat() if fecha else None,
                    "titular": titular, "url": href})
    return out


def team_news(slug):
    return http.cached(f"news_{slug}", CACHE_TTL,
                        lambda: _parse(http.get_text(config.FF_TEAM.format(slug=slug)), slug))


def bad_news_for(nickname, full_name, slug, days=RECENT_DAYS):
    """Recent headlines about this player that smell like transfer/conflict/injury."""
    tokens = [t for t in normalize(f"{nickname} {full_name}").split() if len(t) > 2 and "." not in t]
    hits = []
    cutoff = (datetime.now() - timedelta(days=days)).date().isoformat()
    for n in team_news(slug):
        if n["fecha"] and n["fecha"] < cutoff:
            continue
        low = normalize(n["titular"])
        if not any(t in low.split() for t in tokens if len(t) >= 4):
            continue
        if n["tipo"] in BAD_TYPES or any(w in low for w in BAD_WORDS):
            hits.append(n)
    return hits
