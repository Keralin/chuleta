import io

from chuleta import api


def test_bids_give_up_fast_enough_to_retry_before_the_close(monkeypatch):
    seen = []

    def urlopen(req, timeout):
        seen.append((req.get_method(), timeout))
        return io.BytesIO(b"{}")

    monkeypatch.setattr(api.urllib.request, "urlopen", urlopen)
    c = object.__new__(api.Client)
    c.tokens = {"access_token": "not.a.jwt"}
    c.bid("L", "77", 10)
    c.modify_bid("L", "77", "b1", 10)
    c.market("L")
    assert seen == [("POST", api.BID_TIMEOUT), ("PUT", api.BID_TIMEOUT), ("GET", 30)]
    assert api.BID_TIMEOUT <= 5
