"""Team form from the official calendar: goals for/against per played match,
plus each team's next opponent. Cached 6h; no auth needed."""

import json

from .. import config, http

BASE = f"{config.API}/v1/competition/{config.COMPETITION}"
PLAYED = 7


def _fetch():
    week = json.loads(http.get_text(f"{BASE}/week/current?x-lang=es")).get("weekNumber") or 1
    form, cals = {}, {}
    for w in range(1, week + 2):
        try:
            cals[w] = json.loads(http.get_text(f"{BASE}/calendar?weekNumber={w}&x-lang=es"))
        except Exception:
            continue
        for m in cals[w]:
            if m.get("matchState") == PLAYED and m.get("localScore") is not None:
                for t, gf, gc in ((str(m["localId"]), m["localScore"], m["visitorScore"]),
                                  (str(m["visitorId"]), m["visitorScore"], m["localScore"])):
                    f = form.setdefault(t, {"pj": 0, "gf": 0, "gc": 0})
                    f["pj"] += 1; f["gf"] += gf; f["gc"] += gc
    # The lineup we optimize is for the next OPEN gameweek: once the current
    # week has kicked off (XI frozen) the relevant fixture is next week's.
    cur = cals.get(week, [])
    target = week + 1 if any(m.get("matchState") == PLAYED for m in cur) else week
    nxt = {}
    for m in cals.get(target, []):
        loc, vis = str(m.get("localId")), str(m.get("visitorId"))
        nxt[loc] = {"opp": vis, "home": True}
        nxt[vis] = {"opp": loc, "home": False}
    return {"form": form, "next": nxt, "week": target}


def team_form():
    return http.cached("team_form", 6 * 3600, _fetch)


def goal_diff_per_game(form, team_id):
    f = (form or {}).get(str(team_id))
    if not f or not f["pj"]:
        return 0.0
    return (f["gf"] - f["gc"]) / f["pj"]
