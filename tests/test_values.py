import pytest

from chuleta.strategy import values


def test_a_single_roll_is_worth_the_full_value_on_average():
    """The machine takes no commission: 90%-110% averages out at 100%."""
    assert (values.EXIT_ROLL_MIN + values.EXIT_ROLL_MAX) / 2 == pytest.approx(1.0)


def test_waiting_for_a_good_roll_beats_selling_against_a_deadline():
    assert values.exit_rate(patient=True) > 1.0 > values.exit_rate(patient=False)
    assert values.exit_rate(patient=True) == pytest.approx(1.075)


def test_roll_odds_compound_over_the_days_we_can_wait():
    assert values.roll_odds(0) == 0
    assert values.roll_odds(1) == pytest.approx(0.25)
    assert values.roll_odds(8) == pytest.approx(1 - 0.75 ** 8)
    assert values.roll_odds(8) > values.roll_odds(3)


def test_roll_odds_clamp_outside_the_band():
    assert values.roll_odds(5, threshold=values.EXIT_ROLL_MAX) == 0
    assert values.roll_odds(1, threshold=values.EXIT_ROLL_MIN) == 1


def test_a_deadline_turns_a_thin_flip_negative():
    entry, value, rate = 1_000_000, 1_000_000, 10_000
    patient, _ = values.margin(entry, value, rate, 7, patient=True)
    forced, _ = values.margin(entry, value, rate, 7, patient=False)
    assert patient > 0 > forced


def test_margin_is_reported_against_what_we_paid_not_the_value():
    _, pct = values.margin(500_000, 1_000_000, 0, 7)
    assert pct == pytest.approx((1_000_000 * values.EXIT_PATIENT - 500_000) / 500_000 * 100, abs=0.1)


def test_margin_survives_a_free_entry():
    assert values.margin(0, 1_000_000, 0, 7) == (round(1_000_000 * values.EXIT_PATIENT), 0.0)


def test_projection_is_damped_so_a_week_is_not_extrapolated_straight():
    assert values.project(100, 10, 7) == pytest.approx(100 + 10 * 7 * values.DAMPING)
    assert values.project(100, 10, 7) < 100 + 10 * 7
