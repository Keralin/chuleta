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


def test_cron_line_fires_five_minutes_before_the_madrid_cycle_all_year():
    # every hour at the minute, gated on Madrid's hour: right in winter and
    # summer, whatever the server's own time zone
    line = sniper.cron_line(15, 24, "cd /srv/chuleta && python3 -m chuleta sniper ejecutar")
    assert line == ('19 * * * * [ "$(TZ=Europe/Madrid date +\\%H)" = 15 ] '
                    '&& cd /srv/chuleta && python3 -m chuleta sniper ejecutar >> sniper.log 2>&1')
    assert sniper.cron_line(0, 2, "x").startswith('57 * * * * [ "$(TZ=Europe/Madrid date +\\%H)" = 23 ]')


class Market:
    def __init__(self, close):
        self.close = close

    def market(self, league_id):
        return [{"expirationDate": self.close}]


def test_cycle_is_read_in_madrid_time_in_winter_and_summer():
    assert sniper.cycle_local(Market("2026-11-28T14:24:00+00:00"), "l") == (15, 24)
    assert sniper.cycle_local(Market("2026-06-28T13:24:00+00:00"), "l") == (15, 24)


def test_round_caps_are_bumped_so_a_rival_never_ties_us():
    assert sniper.unround(36_000_000) == 36_001_000
    assert sniper.unround(7_500_000) == 7_501_000
    assert sniper.unround(36_001_000) == 36_001_000  # already unround, left alone
    assert sniper.unround(10_442_335) == 10_442_335


def test_arm_stores_the_unrounded_cap(tmp_path, monkeypatch):
    monkeypatch.setattr(sniper, "PLAN", str(tmp_path / "sniper.json"))
    plan = sniper.arm("77", 15_000_000)
    assert plan == [{"market_id": "77", "cap": 15_001_000}]


class FlakyClient(FakeClient):
    """The first bid times out on the network, the second goes through."""

    def bid(self, league_id, market_id, money):
        self.calls.append(("bid", money))
        if len(self.calls) == 1:
            raise TimeoutError("read timed out")
        return {"ok": True}


def test_a_network_failure_on_the_bid_is_retried_while_time_is_left():
    c = FlakyClient(_close_in(10))
    sniper.snipe(c, "L", "77", cap=9_000_000, log=lambda *a: None, sleep=lambda s: None)
    assert c.calls == [("bid", 5_000_010), ("bid", 5_000_010)]


def test_a_network_failure_past_the_close_gives_up():
    c = FlakyClient(_close_in(1))
    assert sniper.snipe(c, "L", "77", cap=9_000_000, log=lambda *a: None, sleep=lambda s: None) is None
    assert c.calls == [("bid", 5_000_010)]
