"""When each gameweek opens, which is the only deadline that matters.

The lineup freezes when the first match of the gameweek kicks off and that
same XI scores every match of it, postponed ones included. So the number to
know is not when the gameweek ends but when its earliest match starts.
"""

from datetime import datetime


def _when(match):
    raw = match.get("matchDate") or match.get("date")
    try:
        return datetime.fromisoformat(str(raw))
    except (TypeError, ValueError):
        return None


def window(matches):
    """(first kickoff, last kickoff, how many) of a `calendar` payload."""
    times = sorted(t for t in (_when(m) for m in matches) if t)
    if not times:
        return None, None, len(matches)
    return times[0], times[-1], len(matches)


def scheduled(first, last, count):
    """False when the gameweek has no real kickoff times yet: the API answers
    with the same placeholder hour for every match until they are set."""
    return not (count > 1 and first is not None and first == last)


def until(when, now):
    """How long until `when`, for a report: '6d 5h', '20h', '35min', 'ya'."""
    if when is None:
        return "?"
    minutes = (when - now).total_seconds() / 60
    if minutes <= 0:
        return "ya"
    if minutes < 60:
        return f"{minutes:.0f}min"
    hours = minutes / 60
    if hours < 48:
        return f"{hours:.0f}h"
    days, rest = divmod(hours, 24)
    return f"{days:.0f}d {rest:.0f}h"
