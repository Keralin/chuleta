"""Value curves from the API's own daily history: current value, daily rate,
a damped projection, and what the exit is actually worth.

The machine rolls its buy offer fresh every day, somewhere between 90% and
110% of the player's value. There is no commission: a single roll is worth
100% of value on average. What the exit is worth depends only on whether you
can wait for a good one. Hold out for a roll over the threshold and the exit
is worth more than the value; sell against a deadline and you take the dice
as they fall.
"""

from datetime import datetime, timedelta

DAMPING = 0.7        # rises slow down; do not extrapolate a week of +5%/day linearly

EXIT_ROLL_MIN = 0.90    # the machine never offers less than this share of value
EXIT_ROLL_MAX = 1.10    # nor more
EXIT_THRESHOLD = 1.05   # the roll we hold out for
EXIT_PATIENT = (EXIT_THRESHOLD + EXIT_ROLL_MAX) / 2  # 1.075, mean of the rolls we accept
EXIT_FORCED = 0.95      # lower quartile: the planning figure when a deadline sells for us

BUY_MARGIN_PCT = 8.0    # margin at the patient exit below which a flip is not worth doing


def _day(entry):
    return datetime.fromisoformat(str(entry["date"])[:10])


def curve(client, player_id, window=7):
    """(value, daily_rate) over the last `window` days, or None without data."""
    try:
        hist = sorted(client.value_history(player_id), key=_day)
    except Exception:
        return None
    if len(hist) < 2:
        return None
    cutoff = _day(hist[-1]) - timedelta(days=window)
    pts = [h for h in hist if _day(h) >= cutoff]
    if len(pts) < 2:
        return None
    days = (_day(pts[-1]) - _day(pts[0])).days or 1
    last = int(pts[-1]["marketValue"])
    return last, (last - int(pts[0]["marketValue"])) / days


def project(value, rate, horizon):
    return value + rate * horizon * DAMPING


def roll_odds(days, threshold=EXIT_THRESHOLD):
    """Odds of seeing at least one offer >= `threshold` in `days` daily rolls."""
    span = EXIT_ROLL_MAX - EXIT_ROLL_MIN
    per_day = min(max((EXIT_ROLL_MAX - threshold) / span, 0.0), 1.0)
    return 1 - (1 - per_day) ** max(int(days), 0)


def exit_rate(patient=True):
    """What a sale is worth as a share of value, waiting for a roll or not."""
    return EXIT_PATIENT if patient else EXIT_FORCED


def margin(entry_price, value, rate, horizon, patient=True):
    """Resale margin at `horizon`, in EUR and % of the entry.

    `patient` holds out for a roll over the threshold; without it the sale is
    priced as a deadline sale, where the dice fall where they fall.
    """
    proj = project(value, rate, horizon) * exit_rate(patient)
    m = proj - entry_price
    return round(m), round(m / entry_price * 100, 1) if entry_price else 0.0
