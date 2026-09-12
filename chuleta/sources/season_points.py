"""Player fantasy points for the last 3 completed seasons, from futbolfantasy.com.

`last_season.py` only ever gives ONE prior season, through a legacy API host
that goes down regularly (see its docstring). futbolfantasy.com publishes a
full per-player points table for every season back to 2019/20 — every squad
player, not a top-N leaderboard — with the same "Ptos. Fantasy" metric LaLiga
itself uses. This gives `lineup.points_per_game` a sturdier multi-season base,
especially early in a new season when this-year data is still thin.
"""

import re

from .. import http, config
from ..matching import normalize

CACHE_TTL = 7 * 86400  # frozen seasons: a weekly refresh is just caution

# `year` -> the season it represents (year N means season (N-1)/N). Most
# recent COMPLETED season first; the current season is read live from the
# official API, never from here.
SEASON_YEARS = (2026, 2025, 2024)  # 25/26, 24/25, 23/24

# Weight given to each season above when blending, most-recent first,
# renormalized over whichever ones a given player actually has data for.
WEIGHTS = (0.5, 0.3, 0.2)

_NAME_RE = re.compile(r'dtlink_player[^>]*>(?:.*?<img[^>]*>)?\s*([^<]+?)\s*</a>', re.S)
_CELL_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.S)


def _clean(text):
    return re.sub(r"\s+", " ", text).strip()


def parse(html):
    """{normalized_name: {'total': int, 'games': int, 'per_game': float}}.

    Games played is always the first stat column right after the name; the
    "Ptos. Fantasy" total/per-game are always the LAST two columns — anchored
    from the end rather than a fixed column count, since new game modes have
    been added to this table before and would shift a fixed index.
    """
    out = {}
    body = html.split("<tbody>", 1)[-1].split("</tbody>", 1)[0]
    for row in re.findall(r"<tr>(.*?)</tr>", body, re.S):
        name_m = _NAME_RE.search(row)
        if not name_m:
            continue
        cells = [_clean(c) for c in _CELL_RE.findall(row)]
        if len(cells) < 4:
            continue
        try:
            games = int(cells[1])
            total = int(cells[-2])
            per_game = float(cells[-1])
        except ValueError:
            continue
        out[normalize(name_m.group(1))] = {"total": total, "games": games, "per_game": per_game}
    return out


def _fetch(year):
    return parse(http.get_text(config.FF_SEASON_POINTS.format(year=year)))


def season_points(year):
    """Dict normalized_name -> {'total','games','per_game'} for `year` (one of
    SEASON_YEARS). Cached a week; degrades to {} on any failure — a dead
    source must never break scoring, only make it fall back further."""
    try:
        return http.cached(f"season_points_{year}", CACHE_TTL, lambda: _fetch(year))
    except Exception:
        return {}


def history_index():
    """[{season dict}, ...] for SEASON_YEARS, most-recent-first."""
    return [season_points(y) for y in SEASON_YEARS]


def historical_per_game(nickname, name=""):
    """Weighted points/game across the last 3 completed seasons, most-recent
    weighted highest, renormalized over whichever ones this player is found
    in. None if he's in none of them (debutant, promoted canterano, a summer
    arrival from abroad...) so callers can fall further back."""
    entries = []
    for season in history_index():
        entry = None
        for key in (nickname, name):
            if key and normalize(key) in season:
                entry = season[normalize(key)]
                break
        entries.append(entry)
    total_w = sum(w for w, e in zip(WEIGHTS, entries) if e)
    if not total_w:
        return None
    return sum(w * e["per_game"] for w, e in zip(WEIGHTS, entries) if e) / total_w
