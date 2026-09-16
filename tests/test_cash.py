from chuleta.strategy import cash

ME, RIVAL = 1, 2


class FakeClient:
    def __init__(self, feed):
        self.feed = feed

    def standings(self, league_id):
        return [{"team": {"managerId": ME, "manager": {"managerName": "yo"}}},
                {"team": {"managerId": RIVAL, "manager": {"managerName": "rival"}}}]

    def activity(self, league_id, page):
        return self.feed if page == 0 else []


def _caja(rows, name):
    return next(r for r in rows if r["manager"] == name)


def test_transfer_charges_the_buyer_and_pays_the_seller():
    feed = [{"activityTypeId": cash.TRANSFER, "user1Id": RIVAL, "user2Id": ME, "playerMasterId": 9, "amount": 9_000_000}]
    rows = cash.estimate(FakeClient(feed), "L")
    assert _caja(rows, "rival")["caja"] == cash.STARTING_CASH - 9_000_000
    assert _caja(rows, "yo")["caja"] == cash.STARTING_CASH + 9_000_000
    assert _caja(rows, "rival")["traspasos"] == [("compra a", "yo", 9_000_000)]
    assert _caja(rows, "yo")["traspasos"] == [("vende a", "rival", 9_000_000)]


def test_market_buys_sales_and_prizes():
    feed = [{"activityTypeId": cash.BUY, "user1Id": ME, "amount": 5_000_000},
            {"activityTypeId": cash.SALE, "user1Id": ME, "amount": 2_000_000},
            {"activityTypeId": cash.PRIZE, "user1Id": ME, "amount": 700_000}]
    assert _caja(cash.estimate(FakeClient(feed), "L"), "yo")["caja"] == cash.STARTING_CASH - 2_300_000


def test_my_trades_include_transfers_both_ways():
    feed = [{"activityTypeId": cash.TRANSFER, "user1Id": ME, "user2Id": RIVAL, "playerMasterId": 1, "amount": 11_000_000},
            {"activityTypeId": cash.TRANSFER, "user1Id": RIVAL, "user2Id": ME, "playerMasterId": 2, "amount": 9_000_000}]
    buys, sells = cash.my_trades(FakeClient(feed), "L", ME)
    assert buys == {"1": 11_000_000}
    assert sells == {"2": 9_000_000}
