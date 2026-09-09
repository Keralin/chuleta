"""Ghost-mode sniper: bid in the last seconds of an auction, never before.

The plan (market ids and caps) is armed during the day; a cron launches `run`
a few minutes before the league's daily cycle. For each target the loop reads
the live market and, in the final seconds, bids:

- alone (no rival bid): current value + 10 EUR, ~15 s before the close;
- contested: the authorized cap, but only inside the last minute, since the
  bid count is public and an early strike invites a counter-raise. Auctions
  are sealed, so the cap is our one true bid.

Bids are placed on the live market value (never on the stale listing price),
an existing own bid is modified rather than duplicated, and a rejection keeps
whatever bid already stands.
"""

import json
import os
import threading
import time
from datetime import datetime, timezone

from .. import config
from ..api import ApiError

CUSHION = 10
FINAL_ALONE = 15
FINAL_CONTESTED = 60
POLL = 3
MAX_READ_ERRORS = 5
PLAN = os.path.join(config.STATE, "sniper.json")


def _load():
    try:
        with open(PLAN, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save(plan):
    os.makedirs(config.STATE, exist_ok=True)
    with open(PLAN, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=1)


def arm(market_id, cap):
    plan = [t for t in _load() if t["market_id"] != str(market_id)]
    plan.append({"market_id": str(market_id), "cap": int(cap)})
    _save(plan)
    return plan


def clear():
    _save([])


def targets():
    return _load()


def decide(value, rival_bids, seconds_left, cap, alone_final=FINAL_ALONE, contested_final=FINAL_CONTESTED):
    """Amount to bid now, or None to keep waiting."""
    if rival_bids > 0:
        return cap if seconds_left <= contested_final else None
    if seconds_left <= alone_final:
        return min(cap, value + CUSHION)
    return None


def _seconds_left(close_iso, now=None):
    try:
        close = datetime.fromisoformat(close_iso)
    except (TypeError, ValueError):
        return 3600.0
    if close.tzinfo is None:
        close = close.replace(tzinfo=timezone.utc)
    return (close - (now or datetime.now(timezone.utc))).total_seconds()


def snipe(client, league_id, market_id, cap, dry_run=False, log=print, sleep=time.sleep, clock=None):
    """Watch one auction until it closes and bid at the right moment."""
    name, errors = market_id, 0
    while True:
        try:
            market = client.market(league_id)
        except Exception as e:
            errors += 1
            log(f"[sniper] {name}: market read failed ({str(e)[:80]}), retry {errors}/{MAX_READ_ERRORS}")
            if errors >= MAX_READ_ERRORS:
                return None
            sleep(2)
            continue
        el = next((e for e in market if str(e.get("id")) == str(market_id)), None)
        if not el:
            log(f"[sniper] {name}: not in the market any more.")
            return None
        name = el["playerMaster"].get("nickname", market_id)
        value = int(el["playerMaster"].get("marketValue") or 0)
        left = _seconds_left(el.get("expirationDate"), clock() if clock else None)
        mine = el.get("bid")
        rivals = max(0, int(el.get("numberOfBids") or 0) - (1 if mine else 0))
        amount = decide(value, rivals, left, cap)
        if amount is not None and mine and amount <= int(mine.get("money") or 0):
            log(f"[sniper] {name}: standing bid {mine['money']:,} already covers {amount:,}.")
            return None
        if amount is not None:
            if dry_run:
                log(f"[sniper] {name}: WOULD BID {amount:,} (rivals={rivals}, {int(left)}s left)")
                return {"dry_run": True, "amount": amount}
            try:
                resp = (client.modify_bid(league_id, market_id, mine["id"], amount) if mine
                        else client.bid(league_id, market_id, amount))
            except ApiError as e:
                log(f"[sniper] {name}: bid of {amount:,} rejected ({e}); keeping what stands.")
                return None
            log(f"[sniper] {name}: BID {amount:,} placed (rivals={rivals}, {int(left)}s left)")
            return resp
        if left <= 0:
            log(f"[sniper] {name}: closed without bidding.")
            return None
        sleep(min(30, left - 90) if left > 90 else min(POLL, max(1, left - FINAL_ALONE)))


def run(client, league_id, dry_run=False, log=print):
    plan = _load()
    if not plan:
        return
    log(f"[sniper] {len(plan)} target(s)")
    threads = [threading.Thread(target=snipe, kwargs=dict(client=client, league_id=league_id, market_id=t["market_id"],
                                                          cap=t["cap"], dry_run=dry_run, log=log), daemon=True) for t in plan]
    for th in threads:
        th.start()
    for th in threads:
        th.join(timeout=1200)  # a wedged call must never keep the cron alive for hours
    if not dry_run:
        clear()


def cycle_utc(client, league_id):
    """(hour, minute) in UTC at which this league's auctions resolve, read from
    the listings' expiration times. None if the market is empty."""
    for e in client.market(league_id):
        try:
            close = datetime.fromisoformat(e["expirationDate"]).astimezone(timezone.utc)
            return close.hour, close.minute
        except (KeyError, TypeError, ValueError):
            continue
    return None


def cron_line(hour_utc, minute_utc, lead_minutes=5, command="chuleta sniper ejecutar"):
    m = minute_utc - lead_minutes
    h = hour_utc
    if m < 0:
        m += 60
        h = (h - 1) % 24
    return f"{m} {h} * * * cd $HOME && {command} >> sniper.log 2>&1"
