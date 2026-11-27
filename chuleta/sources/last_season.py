"""Last season's total points from the LEGACY API host.

The 26/27 API renumbered player ids, so `lastSeasonPoints` comes back null for
~285 players (Dani Olmo included). The old host is frozen at the 25/26 season:
its `points` field IS last season's total. Matched by normalized name.
"""

import json

from .. import http
from ..matching import normalize

from .. import config
LEGACY_PLAYERS_URL = config.LEGACY_PLAYERS
_down = False
CACHE_TTL = 86400  # frozen data: refresh daily out of caution, it never changes


def _fetch():
    players = json.loads(http.get_text(LEGACY_PLAYERS_URL))
    out = {}
    for p in players:
        pts = p.get("points")
        if pts is None:
            continue
        for key in (p.get("nickname"), p.get("name")):
            if key:
                out[normalize(key)] = pts
    return out


def points_index():
    """Dict normalized_name -> total points in 25/26 (cached 24h).

    The legacy host goes down now and then (502s); an outage must degrade to
    "?" in the reports, never kill the screening. The failure is not cached
    on disk, so the next run tries again.
    """
    global _down
    if _down:
        return {}
    try:
        return http.cached("last_season_points", CACHE_TTL, _fetch)
    except Exception:
        # one failed fetch per run: retried per player, a dead host kept
        # `bajas` waiting on back-offs for more than ten minutes
        _down = True
        return {}


def last_season_points(nickname, name=""):
    idx = points_index()
    for key in (nickname, name):
        if key and normalize(key) in idx:
            return idx[normalize(key)]
    return None
