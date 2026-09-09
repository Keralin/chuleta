from datetime import datetime, timedelta, timezone

from chuleta.strategy import sniper


def test_policy_alone_bids_value_plus_cushion_only_at_the_end():
    assert sniper.decide(1_000_000, 0, 300, 2_000_000) is None
    assert sniper.decide(1_000_000, 0, 14, 2_000_000) == 1_000_010


def test_policy_contested_bids_the_cap_inside_the_last_minute():
    assert sniper.decide(1_000_000, 2, 300, 1_500_000) is None
    assert sniper.decide(1_000_000, 2, 45, 1_500_000) == 1_500_000


def test_cap_never_exceeded_when_alone():
    assert sniper.decide(1_000_000, 0, 5, 1_000_005) == 1_000_005


class FakeClient:
    def __init__(self, close, bids=0, mine=None, value=5_000_000):
        self.close, self.bids, self.mine, self.value = close, bids, mine, value
        self.calls = []

    def market(self, league_id):
        return [{"id": "77", "expirationDate": self.close, "numberOfBids": self.bids, "bid": self.mine,
                 "playerMaster": {"nickname": "Test", "marketValue": self.value}}]

    def bid(self, league_id, market_id, money):
        self.calls.append(("bid", money)); return {"ok": True}

    def modify_bid(self, league_id, market_id, bid_id, money):
        self.calls.append(("modify", bid_id, money)); return {"ok": True}


def _close_in(seconds):
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()


def test_alone_places_value_plus_ten_on_live_value():
    c = FakeClient(_close_in(10))
    sniper.snipe(c, "L", "77", cap=9_000_000, log=lambda *a: None, sleep=lambda s: None)
    assert c.calls == [("bid", 5_000_010)]


def test_contested_modifies_own_bid_instead_of_duplicating():
    c = FakeClient(_close_in(30), bids=2, mine={"id": "b1", "money": 5_000_010})
    sniper.snipe(c, "L", "77", cap=6_000_000, log=lambda *a: None, sleep=lambda s: None)
    assert c.calls == [("modify", "b1", 6_000_000)]


def test_cron_line_fires_five_minutes_before_the_cycle():
    assert sniper.cron_line(13, 24).startswith("19 13 * * *")
    assert sniper.cron_line(0, 2).startswith("57 23 * * *")
