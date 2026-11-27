from chuleta.sources import last_season


def test_a_dead_legacy_host_is_tried_once_per_run_not_once_per_player(monkeypatch):
    calls = []

    def down():
        calls.append(1)
        raise OSError("HTTP Error 500")

    monkeypatch.setattr(last_season, "_fetch", down)
    monkeypatch.setattr(last_season, "_down", False)
    assert last_season.last_season_points("Isco") is None
    assert last_season.last_season_points("Fornals") is None
    assert len(calls) == 1
