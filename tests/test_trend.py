from chuleta.strategy import trend


def history(*values):
    return [{"date": f"2026-09-{10 + i:02d}", "marketValue": v} for i, v in enumerate(values)]


def test_deltas_sorted_by_date_even_if_the_payload_is_not():
    payload = list(reversed(history(10, 12, 15)))
    values, changes = trend.deltas(payload)
    assert values == [10, 12, 15]
    assert changes == [2, 3]


def test_streak_counts_only_the_run_that_ends_today():
    assert trend.streak([5, -3, -2, -4]) == (-1, 3)
    assert trend.streak([-5, 3, 2]) == (1, 2)
    assert trend.streak([]) == (0, 0)


def test_acceleration_is_negative_when_the_daily_rise_shrinks():
    assert trend.acceleration([900, 700, 500, 300]) == -200
    assert trend.acceleration([300, 500, 700, 900]) == +200
    assert trend.acceleration([100, 200]) == 0.0  # not enough days yet


def test_summary_reads_a_riser_that_is_braking():
    s = trend.summary(history(10_000_000, 10_900_000, 11_600_000, 12_100_000, 12_400_000))
    assert s["valor"] == 12_400_000
    assert s["hoy"] == 300_000
    assert round(s["pct"], 2) == 2.48
    assert (s["sentido"], s["racha"]) == ("sube", 4)
    assert s["aceleracion"] < 0


def test_summary_needs_two_days():
    assert trend.summary(history(10)) is None
    assert trend.summary([]) is None


def test_the_live_value_counts_as_today_when_the_history_lags():
    # the history stops yesterday, the API already reports today's roll
    s = trend.summary(history(10_000_000, 10_900_000, 11_600_000), live=12_100_000)
    assert s["valor"] == 12_100_000
    assert s["hoy"] == 500_000
    assert s["racha"] == 3


def test_a_live_value_equal_to_the_last_point_adds_no_day():
    s = trend.summary(history(10_000_000, 10_900_000, 11_600_000), live=11_600_000)
    assert s["valor"] == 11_600_000
    assert s["hoy"] == 700_000
    assert s["racha"] == 2


def test_without_a_live_value_nothing_changes():
    assert trend.summary(history(10_000_000, 10_900_000)) == trend.summary(
        history(10_000_000, 10_900_000), live=None)


def test_the_live_value_can_turn_a_rise_into_a_fall():
    s = trend.summary(history(10_000_000, 10_900_000, 11_600_000), live=11_300_000)
    assert s["hoy"] == -300_000
    assert s["sentido"] == "baja"
    assert s["racha"] == 1


def test_one_history_point_plus_the_live_value_is_enough():
    s = trend.summary(history(10_000_000), live=10_400_000)
    assert s is not None and s["hoy"] == 400_000
