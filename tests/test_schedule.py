from datetime import datetime, timedelta, timezone

from chuleta.strategy import schedule

NOW = datetime(2026, 10, 3, 16, 0, tzinfo=timezone.utc)


def matches(*iso):
    return [{"matchDate": t} for t in iso]


def test_the_window_is_the_earliest_and_latest_kickoff_whatever_the_order():
    first, last, n = schedule.window(matches(
        "2026-10-11T16:15:00+02:00", "2026-10-09T21:00:00+02:00", "2026-10-13T03:00:00+02:00"))
    assert first.isoformat() == "2026-10-09T21:00:00+02:00"
    assert last.isoformat() == "2026-10-13T03:00:00+02:00"
    assert n == 3


def test_an_unparseable_kickoff_is_dropped_without_losing_the_count():
    first, last, n = schedule.window(matches("2026-10-09T21:00:00+02:00", "manana"))
    assert first == last and n == 2


def test_an_empty_gameweek_has_no_window():
    assert schedule.window([]) == (None, None, 0)


def test_a_missing_kickoff_falls_back_to_the_date_field():
    first, _, _ = schedule.window([{"date": "2026-10-09T21:00:00+02:00"}])
    assert first is not None


def test_days_and_hours_for_a_gameweek_next_week():
    assert schedule.until(NOW + timedelta(days=6, hours=3), NOW) == "6d 3h"


def test_hours_alone_under_two_days():
    assert schedule.until(NOW + timedelta(hours=20), NOW) == "20h"


def test_minutes_when_the_freeze_is_imminent():
    assert schedule.until(NOW + timedelta(minutes=30), NOW) == "30min"


def test_a_kickoff_already_past_reads_as_started():
    assert schedule.until(NOW - timedelta(hours=1), NOW) == "ya"
    assert schedule.until(NOW, NOW) == "ya"


def test_no_kickoff_is_not_a_crash():
    assert schedule.until(None, NOW) == "?"


def test_a_gameweek_without_real_kickoff_times_is_flagged():
    first, last, n = schedule.window(matches(
        "2026-11-01T01:00:00+01:00", "2026-11-01T01:00:00+01:00", "2026-11-01T01:00:00+01:00"))
    assert schedule.scheduled(first, last, n) is False


def test_a_gameweek_with_real_times_is_not_flagged():
    first, last, n = schedule.window(matches(
        "2026-10-09T21:00:00+02:00", "2026-10-12T21:00:00+02:00"))
    assert schedule.scheduled(first, last, n) is True


def test_a_single_match_gameweek_is_not_flagged_as_unscheduled():
    first, last, n = schedule.window(matches("2026-10-09T21:00:00+02:00"))
    assert schedule.scheduled(first, last, n) is True
