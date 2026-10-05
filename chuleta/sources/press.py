"""futbolfantasy probable lineups: per club, each player's starting odds and
injury / suspension flags, read from the shirt tags on the club page."""

import re
import sys

from .. import config, http
from ..matching import normalize

CACHE_TTL = 30 * 60


def club_slugs():
    html = http.get_text(config.FF_LINEUPS)
    return sorted(set(re.findall(r"/laliga/equipos/([a-z0-9-]+)", html)))


def _attr(tag, name):
    m = re.search(rf'{name}="([^"]*)"', tag)
    return m.group(1) if m else None


def club_lineup(slug):
    html = http.get_text(config.FF_TEAM.format(slug=slug))
    players = {}
    for tag in re.findall(r'<a class="camiseta[^>]*>', html):
        m = re.search(r"/jugadores/([a-z0-9-]+)", _attr(tag, "href") or "")
        if not m:
            continue
        pslug = m.group(1)
        prob = (_attr(tag, "data-probabilidad") or "").rstrip("%")
        injured = _attr(tag, "data-lesion") not in (None, "-1", "0")
        unavailable = _attr(tag, "data-sancionado") == "1" or _attr(tag, "data-nodisponible") == "1"
        entry = {"slug": pslug, "nombre": pslug.replace("-", " "), "equipo": slug,
                 "prob": int(prob) if prob.isdigit() else None,
                 "lesionado": injured, "disponible": not unavailable}
        old = players.get(pslug)
        if old is None or (entry["prob"] or 0) > (old["prob"] or 0):
            players[pslug] = entry
    return list(players.values())


def _index(slugs):
    idx = {}
    for slug in slugs:
        try:
            for p in club_lineup(slug):
                idx[normalize(p["nombre"])] = p
        except Exception as e:
            print(f"[aviso] prensa {slug}: {e}", file=sys.stderr)
    return idx


def probable_lineups(slugs=None):
    """normalized name -> press entry, all clubs, cached 30 min."""
    if slugs is not None:
        return _index(slugs)
    return http.cached("press_index", CACHE_TTL, lambda: _index(club_slugs()))


def condition(entry, api_status=None):
    """('out' | 'doubt' | 'fit', reason) from the press entry and the API status.

    The press keeps its injury tag on a player long after he is fit, and its
    starting odds do not separate the two cases: Luismi Cruz carried the tag at
    80% while his club had him training apart and ruled him out, and Bellerín
    carried it at 70% on a day the press expected him to start. Both clubs even
    announced it in nearly the same words. So the tag is a doubt to resolve by
    reading the club news, never a status on its own. Only the API status or a
    suspension makes it an absence.
    """
    prob = (entry or {}).get("prob")
    odds = f"{prob}% de ser titular" if prob is not None else "sin probabilidad"
    if api_status and api_status != "ok":
        return "out", f"estado {api_status}"
    if entry and not entry.get("disponible", True):
        return "out", "sancionado o no disponible según la prensa"
    if entry and entry.get("lesionado"):
        return "doubt", f"la prensa lo marca lesionado ({odds}), sin confirmar"
    return "fit", ""


def club_slug(club_name, slugs):
    """'Deportivo Alavés' -> 'alaves': the slug whose words all appear in the
    name, preferring the one covering the distinctive last word."""
    words = normalize(club_name).split()
    hits = [s for s in slugs if set(s.split("-")) <= set(words)]
    if not hits:
        return None
    return max(hits, key=lambda s: (words[-1] in s.split("-"), len(s)))
