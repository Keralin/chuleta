"""Where a player's value is heading, read from his daily value history.

Three numbers decide when to sell: today's change, how many days in a row it
has moved the same way, and whether those daily changes are growing or
shrinking. A player who still rises but rises less every day is about to turn,
and that is the moment to list him — not three days later, when the machine
already offers less.
"""

ACCELERATION_WINDOW = 4  # days compared to judge whether the daily change grows


def deltas(history):
    """Day-to-day changes from a `value_history` payload (oldest first)."""
    values = [int(h["marketValue"]) for h in sorted(history, key=lambda h: str(h["date"]))]
    return values, [b - a for a, b in zip(values, values[1:])]


def streak(changes):
    """(direction, days) of the run that ends today: +1 rising, -1 falling."""
    if not changes:
        return 0, 0
    way = 1 if changes[-1] > 0 else -1
    days = 0
    for change in reversed(changes):
        if change * way <= 0:
            break
        days += 1
    return way, days


def acceleration(changes, window=ACCELERATION_WINDOW):
    """Change per day of the daily change itself: negative means braking."""
    if len(changes) < window:
        return 0.0
    return (changes[-1] - changes[-window]) / (window - 1)


def summary(history):
    """Everything worth knowing about one player's value, or None without data."""
    values, changes = deltas(history)
    if len(values) < 2:
        return None
    way, days = streak(changes)
    return {
        "valor": values[-1],
        "hoy": changes[-1],
        "pct": changes[-1] / values[-2] * 100 if values[-2] else 0.0,
        "sentido": "sube" if way > 0 else "baja",
        "racha": days,
        "aceleracion": acceleration(changes),
        "ultimos": changes[-5:],
    }
