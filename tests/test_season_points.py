from chuleta.sources.season_points import parse, historical_per_game

SAMPLE_HTML = """
<table id="dtStatsJugador">
<thead><tr><th>Jugador</th><th>P</th><th>Picas</th><th>Ptos. Fantasy</th><th>Ptos. Fantasy/P</th></tr></thead>
<tbody>
<tr>
    <td>
        <a href="https://www.futbolfantasy.com/jugadores/fermin-lopez" class="link dtlink_player">
            <img class="dtavatar_player" src="x.png" />
            Fermín López
        </a>
    </td>
    <td>31</td>
    <td>31</td>
    <td>271</td>
    <td>8.74</td>
</tr>
<tr>
    <td>
        <a href="https://www.futbolfantasy.com/jugadores/x" class="link dtlink_player">
            <img class="dtavatar_player" src="x.png" />
            Nobody
        </a>
    </td>
    <td>0</td>
    <td>0</td>
    <td>0</td>
    <td>0</td>
</tr>
</tbody>
</table>
"""


def test_parse_reads_name_games_and_fantasy_points():
    data = parse(SAMPLE_HTML)
    assert data["fermin lopez"] == {"total": 271, "games": 31, "per_game": 8.74}
    assert data["nobody"] == {"total": 0, "games": 0, "per_game": 0.0}


def test_historical_per_game_weights_recent_seasons_more(monkeypatch):
    from chuleta.sources import season_points

    seasons = [
        {"fermin lopez": {"total": 300, "games": 30, "per_game": 10.0}},  # 25/26
        {"fermin lopez": {"total": 271, "games": 31, "per_game": 8.74}},  # 24/25
        {},                                                              # 23/24: no data
    ]
    monkeypatch.setattr(season_points, "history_index", lambda: seasons)

    result = historical_per_game("Fermín", "Fermín López")
    # renormalized over the 2 seasons with data: weights 0.5 and 0.3
    expected = (0.5 * 10.0 + 0.3 * 8.74) / 0.8
    assert abs(result - expected) < 1e-9


def test_historical_per_game_none_when_absent_everywhere(monkeypatch):
    from chuleta.sources import season_points

    monkeypatch.setattr(season_points, "history_index", lambda: [{}, {}, {}])
    assert historical_per_game("Nadie de Nadie") is None
