"""Value curves from the API's own daily history: current value, daily rate
and a damped projection. The exit haircut through the machine averages 0-5%."""

from datetime import datetime, timedelta

DAMPING = 0.7        # rises slow down; do not extrapolate a week of +5%/day linearly
EXIT_HAIRCUT = 0.03  # machine offers average ~97% of value on a random roll


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


def margin(entry_price, value, rate, horizon):
    """Expected resale margin after the haircut, in EUR and % of the entry."""
    proj = project(value, rate, horizon) * (1 - EXIT_HAIRCUT)
    m = proj - entry_price
    return round(m), round(m / entry_price * 100, 1) if entry_price else 0.0
