from datetime import datetime, timedelta, timezone

from chuleta.strategy import clauses

NOW = datetime(2026, 10, 3, 15, 0, tzinfo=timezone.utc)


def test_a_window_closing_tonight_is_not_reported_as_open():
    hours = clauses._hours_locked((NOW + timedelta(hours=20)).isoformat(), NOW)
    assert round(hours) == 20
    assert clauses.opens_in(hours) == "abre en 20h"


def test_an_expired_window_reads_as_open():
    hours = clauses._hours_locked((NOW - timedelta(days=3)).isoformat(), NOW)
    assert hours == 0.0
    assert clauses.opens_in(hours) == "ya abierta"


def test_no_timestamp_reads_as_open():
    assert clauses._hours_locked(None, NOW) == 0.0
    assert clauses.opens_in(clauses._hours_locked("", NOW)) == "ya abierta"


def test_a_naive_timestamp_does_not_crash():
    assert clauses._hours_locked("2026-10-16T15:24:00", NOW) == 0.0


def test_garbage_does_not_crash():
    assert clauses._hours_locked("manana", NOW) == 0.0


def test_a_long_window_is_reported_in_days():
    hours = clauses._hours_locked((NOW + timedelta(days=13, hours=2)).isoformat(), NOW)
    assert clauses.opens_in(hours) == "abre en 13.1d"


class _FakeClient:
    def __init__(self, stats):
        self._stats = stats

    def player(self, player_id):
        return {"playerStats": self._stats}


def stat(week, mins, points):
    return {"weekNumber": week, "totalPoints": points, "stats": {"mins_played": [mins]}}


def test_usage_counts_only_the_games_he_actually_played():
    pj, mins, ppg = clauses.usage(_FakeClient([
        stat(1, 90, 6), stat(2, 0, 0), stat(3, 45, 3)]), "1")
    assert (pj, mins) == (2, 135)
    assert ppg == 4.5


def test_usage_of_a_player_who_never_played():
    assert clauses.usage(_FakeClient([stat(1, 0, 0)]), "1") == (0, 0, 0.0)


def test_usage_ignores_entries_without_a_gameweek():
    pj, mins, _ = clauses.usage(_FakeClient([stat(1, 90, 6), {"stats": {"mins_played": [90]}}]), "1")
    assert (pj, mins) == (1, 90)
