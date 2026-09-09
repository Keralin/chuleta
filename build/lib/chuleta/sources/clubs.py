"""teamId -> club name. The public player list only carries opaque team ids;
squads and market entries embed the team object, so one pass over the league
maps every club present. Cached for a week."""

from .. import http

CACHE_TTL = 7 * 86400

# Ids seen in API payloads during 26/27. The harvest below overrides and extends
# this; the seed only guarantees a name for clubs no league manager owns yet.
SEED = {"2": "Atlético de Madrid", "3": "Athletic Club", "4": "FC Barcelona", "5": "Real Betis",
        "6": "Celta", "7": "Elche CF", "8": "RCD Espanyol", "9": "Getafe CF", "11": "Levante UD",
        "12": "Málaga CF", "13": "C.A. Osasuna", "14": "Rayo Vallecano", "15": "Real Madrid",
        "16": "Real Sociedad", "17": "Sevilla FC", "18": "Valencia CF", "20": "Villarreal CF",
        "21": "Deportivo Alavés", "26": "RC Deportivo", "49": "R. Racing Club"}


def club_names(client):
    def harvest():
        league_id, _ = client.default_ids()
        names = dict(SEED)

        def grab(pm):
            team = (pm or {}).get("team") or {}
            if team.get("id") and team.get("name"):
                names[str(team["id"])] = team["name"]

        for s in client.standings(league_id):
            for p in client.team(league_id, str(s["team"]["id"])).get("players", []):
                grab(p.get("playerMaster"))
        for e in client.market(league_id):
            grab(e.get("playerMaster"))
        return names

    return http.cached("club_names", CACHE_TTL, harvest)
