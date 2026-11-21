"""Every manager's cash, rebuilt from the public activity feed.

Rival balances are private, but market buys (type 31), sales to the machine
(33), weekly prizes (6) and manager-to-manager transfers (1) are not. In a
transfer user1 is the buyer and user2 the seller (checked against a trade we
made ourselves). Clause raises are missing from the feed, so real balances
are equal or lower. Everyone starts the season with 100M."""

STARTING_CASH = 100_000_000
BUY, TRANSFER, SALE, PRIZE = 31, 1, 33, 6


def _feed(client, league_id):
    page = 0
    while page < 50:
        acts = client.activity(league_id, page)
        if not acts:
            return
        yield from acts
        page += 1


def estimate(client, league_id, my_team_id=None):
    managers = {int(s["team"]["managerId"]): s["team"]["manager"]["managerName"] for s in client.standings(league_id)}
    book = {uid: {"gastado": 0, "ingresado": 0, "traspasos": []} for uid in managers}
    for a in _feed(client, league_id):
        uid, kind, amount = a.get("user1Id"), a.get("activityTypeId"), a.get("amount") or 0
        if kind == TRANSFER:
            seller = a.get("user2Id")
            if uid in book:
                book[uid]["gastado"] += amount
                book[uid]["traspasos"].append(("compra a", managers.get(seller, "?"), amount))
            if seller in book:
                book[seller]["ingresado"] += amount
                book[seller]["traspasos"].append(("vende a", managers.get(uid, "?"), amount))
        elif uid not in book:
            continue
        elif kind == BUY:
            book[uid]["gastado"] += amount
        elif kind in (SALE, PRIZE):
            book[uid]["ingresado"] += amount
    rows = []
    for uid, name in managers.items():
        b = book[uid]
        rows.append({"manager": name, **b, "caja": STARTING_CASH - b["gastado"] + b["ingresado"]})
    rows.sort(key=lambda r: -r["caja"])
    return rows


def my_trades(client, league_id, my_user_id):
    """(held, realized) from the feed, including transfers with other managers.

    held: {playerMasterId: cost} for players bought and not sold since.
    realized: [(playerMasterId, cost or None, sale)] oldest first; cost is None
    for a player from the starting squad.

    The feed comes newest first, so it is replayed oldest first: a player sold
    and bought back must pair each sale with its own buy."""
    held, realized = {}, []
    for a in reversed(list(_feed(client, league_id))):
        pid, kind = str(a.get("playerMasterId")), a.get("activityTypeId")
        if a.get("user1Id") == my_user_id and kind in (BUY, TRANSFER):
            held[pid] = a["amount"]
        elif (a.get("user1Id") == my_user_id and kind == SALE) or (kind == TRANSFER and a.get("user2Id") == my_user_id):
            realized.append((pid, held.pop(pid, None), a["amount"]))
    return held, realized
