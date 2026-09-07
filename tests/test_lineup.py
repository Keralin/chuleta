from chuleta.strategy.lineup import optimize, points_per_game, fixture_factor


def player(pid, pos, nick, value, avg=None, pts=None, status="ok", last=None, team="1"):
    return {"playerTeamId": pid, "playerMaster": {"id": pid, "nickname": nick, "name": nick, "positionId": pos,
            "marketValue": value, "averagePoints": avg, "points": pts, "playerStatus": status,
            "lastSeasonPoints": last, "team": {"id": team}}}


def squad():
    s = [player("g", 1, "gk", 10e6, 6, 24)]
    s += [player(f"d{i}", 2, f"def{i}", 5e6, 3 + i * 0.5, 12) for i in range(5)]
    s += [player(f"m{i}", 3, f"mid{i}", 8e6, 4 + i * 0.5, 16) for i in range(4)]
    s += [player(f"f{i}", 4, f"fwd{i}", 12e6, 5 + i, 20) for i in range(3)]
    return {"players": s}


def test_expected_points_prefers_scorers_over_odds():
    press = {"def4": {"prob": 90}, "fwd2": {"prob": 40}, "fwd0": {"prob": 90}}
    best = optimize(squad(), press=press, form=None)
    names = [e["nombre"] for e in best["striker"]]
    assert "fwd2" in names  # 0.4 x 7 = 2.8 beats fwd0's 0.9 x 5 = 4.5? no: both fit in 3 slots


def test_injured_never_fielded_when_alternatives_exist():
    s = squad(); s["players"][1]["playerMaster"]["playerStatus"] = "injured"
    best = optimize(s, press={}, form=None)
    assert all(e["nombre"] != "def0" for e in best["defender"])


def test_played_last_week_counts_as_starter():
    press = {"fwd0": {"prob": 90}, "fwd1": {"prob": 90}, "fwd2": None}
    press = {k: v for k, v in press.items() if v}
    best = optimize(squad(), press=press, form=None, recent_minutes={"f2": 75})
    assert any(e["tag"] == "jugó la última" for e in best["striker"])


def test_blend_uses_last_season_when_sample_is_short():
    pm = {"averagePoints": 10, "points": 10, "lastSeasonPoints": 34}
    assert 1 < points_per_game(pm) < 10


def test_fixture_factor_is_neutral_without_data():
    assert fixture_factor({"team": {"id": "1"}, "positionId": 2}, None) == 1.0
