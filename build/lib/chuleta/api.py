"""Client for the LALIGA Fantasy API (unofficial).

Every method returns the parsed JSON. Paths under `/v1/competition/1/...` are
the game itself; the token is refreshed when it is about to expire or on 401.
Ids: `league_id` and `team_id` come from `default_ids()`; players carry two
ids, `playerMaster.id` (the footballer) and `playerTeamId` (his slot in a
squad); market entries have their own `id` (the auction).
"""

import json
import time
import urllib.error
import urllib.request

from . import auth, config


class ApiError(Exception):
    pass


class Client:
    def __init__(self):
        self.tokens = auth.load_tokens()

    # --- transport -------------------------------------------------------
    def _call(self, method, path, body=None, retry=True):
        if auth.expiring(self.tokens):
            self.tokens = auth.refresh(self.tokens)
        data = json.dumps(body).encode() if body is not None else None
        headers = {"Authorization": f"Bearer {auth.bearer(self.tokens)}", "Accept": "application/json",
                   "x-lang": "es", "User-Agent": config.USER_AGENT}
        if data is not None:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(config.API + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                raw = r.read().decode()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as e:
            if e.code == 401 and retry:
                self.tokens = auth.refresh(self.tokens)
                return self._call(method, path, body, retry=False)
            raise ApiError(f"{method} {path} -> {e.code}: {e.read().decode('utf-8', 'replace')[:300]}")

    def get(self, path):
        return self._call("GET", path)

    def post(self, path, body=None):
        return self._call("POST", path, body)

    def put(self, path, body=None):
        return self._call("PUT", path, body)

    def delete(self, path):
        return self._call("DELETE", path)

    @staticmethod
    def c(tail):
        return f"/v1/competition/{config.COMPETITION}{tail}"

    # --- account -----------------------------------------------------------
    def me(self):
        return self.get("/v4/user/me?x-lang=es")

    def leagues(self):
        return self.get(self.c("/leagues?x-lang=es"))

    def default_ids(self):
        leagues = self.leagues()
        if not leagues:
            raise ApiError("This account has no leagues.")
        if config.LEAGUE:
            for lg in leagues:
                if str(lg["id"]) == str(config.LEAGUE):
                    return lg["id"], str(lg["team"]["id"])
            raise ApiError(f"League {config.LEAGUE} is not in this account.")
        return leagues[0]["id"], str(leagues[0]["team"]["id"])

    # --- reads ---------------------------------------------------------------
    def team(self, league_id, team_id):
        return self.get(self.c(f"/leagues/{league_id}/teams/{team_id}?x-lang=es"))

    def standings(self, league_id, week=None):
        tail = f"/leagues/{league_id}/standing" + (f"/{week}" if week else "") + "?x-lang=es"
        return self.get(self.c(tail)) or []

    def activity(self, league_id, page):
        return self.get(self.c(f"/leagues/{league_id}/activity/{page}?x-lang=es")) or []

    def players(self):
        return self.get(self.c("/players?x-lang=es")) or []

    def player(self, player_id):
        return self.get(self.c(f"/player/{player_id}?x-lang=es")) or {}

    def value_history(self, player_id):
        return self.get(self.c(f"/player/{player_id}/market-value?x-lang=es")) or []

    def market(self, league_id):
        return self.get(self.c(f"/league/{league_id}/market?x-lang=es")) or []

    def offers(self, league_id, player_team_id):
        return self.get(self.c(f"/league/{league_id}/playerTeam/{player_team_id}/offer?x-lang=es")) or []

    def lineup(self, team_id):
        return self.get(self.c(f"/teams/{team_id}/lineup?x-lang=es"))

    def current_week(self):
        return self.get(self.c("/week/current?x-lang=es")) or {}

    def calendar(self, week):
        return self.get(self.c(f"/calendar?weekNumber={week}&x-lang=es")) or []

    # --- writes (irreversible ones are marked) -------------------------------
    def bid(self, league_id, market_id, money):
        return self.post(self.c(f"/league/{league_id}/market/{market_id}/bid?x-lang=es"), {"money": money})

    def modify_bid(self, league_id, market_id, bid_id, money):
        return self.put(self.c(f"/league/{league_id}/market/{market_id}/bid/{bid_id}?x-lang=es"), {"money": money})

    def cancel_bid(self, league_id, market_id, bid_id):
        return self.delete(self.c(f"/league/{league_id}/market/{market_id}/bid/{bid_id}/cancel?x-lang=es"))

    def offer(self, league_id, market_id, money):
        """Direct offer on another manager's listing (floor: current value)."""
        return self.post(self.c(f"/league/{league_id}/market/{market_id}/offer?x-lang=es"), {"money": money})

    def list_player(self, league_id, player_team_id, price):
        return self.post(self.c(f"/league/{league_id}/market/sell?x-lang=es"),
                         {"playerId": player_team_id, "salePrice": price})

    def unlist_player(self, league_id, market_id):
        return self.delete(self.c(f"/league/{league_id}/market/{market_id}/delete?x-lang=es"))

    def accept_offer(self, league_id, market_id, offer_id, money):  # irreversible
        return self.post(self.c(f"/league/{league_id}/market/{market_id}/offer/{offer_id}/accept?x-lang=es"),
                         {"offerMoney": money})

    def decline_offer(self, league_id, market_id, offer_id):
        return self.post(self.c(f"/league/{league_id}/market/{market_id}/offer/{offer_id}/reject?x-lang=es"))

    def pay_clause(self, league_id, player_team_id, amount):  # irreversible
        return self.post(self.c(f"/league/{league_id}/buyout/{player_team_id}/pay?x-lang=es"),
                         {"buyoutClauseToPay": amount})

    def save_lineup(self, team_id, goalkeeper, defenders, midfielders, forwards):
        return self.put(self.c(f"/teams/{team_id}/lineup?x-lang=es"), {
            "goalkeeper": goalkeeper, "defender": defenders, "midfield": midfielders,
            "striker": forwards, "tactical_formation": [len(defenders), len(midfielders), len(forwards)]})


def club_of(pm, clubs=None):
    """(name, api slug) of a player's club: the embedded team object when the
    payload carries it (squads), else the harvested teamId map (`clubs`)."""
    team = (pm or {}).get("team") or {}
    name = team.get("name") or (clubs or {}).get(str(pm.get("teamId")))
    return name or f"?{pm.get('teamId')}", team.get("slug")
