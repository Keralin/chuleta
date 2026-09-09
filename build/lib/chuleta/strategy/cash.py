"""Every manager's cash, rebuilt from the public activity feed.

Rival balances are private, but market buys (type 31), sales to the machine
(33), weekly prizes (6) and manager-to-manager transfers (1) are not. Clause
raises are missing from the feed, so real balances are equal or lower.
Everyone starts the season with 100M."""

STARTING_CASH = 100_000_000
BUY, TRANSFER, SALE, PRIZE = 31, 1, 33, 6


def estimate(client, league_id, my_team_id=None):
    managers = {int(s["team"]["managerId"]): s["team"]["manager"]["managerName"] for s in client.standings(league_id)}
    book = {uid: {"gastado": 0, "ingresado": 0, "traspasos": []} for uid in managers}
    page = 0
    while page < 50:
        acts = client.activity(league_id, page)
        if not acts:
            break
        for a in acts:
            uid, kind, amount = a.get("user1Id"), a.get("activityTypeId"), a.get("amount") or 0
            if uid not in book:
                continue
            if kind == BUY:
                book[uid]["gastado"] += amount
            elif kind in (SALE, PRIZE):
                book[uid]["ingresado"] += amount
            elif kind == TRANSFER:
                book[uid]["traspasos"].append((managers.get(a.get("user2Id"), "?"), amount))
        page += 1
    rows = []
    for uid, name in managers.items():
        b = book[uid]
        rows.append({"manager": name, **b, "caja": STARTING_CASH - b["gastado"] + b["ingresado"]})
    rows.sort(key=lambda r: -r["caja"])
    return rows


def my_trades(client, league_id, my_user_id):
    """{playerMasterId: amount} for our buys and our sales, from the feed."""
    buys, sells = {}, {}
    page = 0
    while page < 50:
        acts = client.activity(league_id, page)
        if not acts:
            break
        for a in acts:
            if a.get("user1Id") != my_user_id:
                continue
            pid = str(a.get("playerMasterId"))
            if a.get("activityTypeId") == BUY:
                buys[pid] = a["amount"]
            elif a.get("activityTypeId") == SALE:
                sells[pid] = a["amount"]
        page += 1
    return buys, sells
