from chuleta.strategy import scout


def press(prob=80, lesionado=False, disponible=True):
    return {"slug": "luismi-cruz", "nombre": "luismi cruz", "equipo": "deportivo",
            "prob": prob, "lesionado": lesionado, "disponible": disponible}


def test_an_unresolved_press_doubt_is_enough_to_pass_on_a_buy():
    v = scout.vetoes("ok", 120_000, 1.0, 7, 5.3, press(lesionado=True), [])
    assert v == ["la prensa lo marca lesionado (80% de ser titular), sin confirmar"]


def test_the_api_status_is_reported_once_not_twice():
    v = scout.vetoes("injured", 120_000, 1.0, 7, 5.3, press(lesionado=True), [])
    assert v == ["estado injured"]


def test_a_suspended_player_is_vetoed():
    v = scout.vetoes("ok", 120_000, 1.0, 7, 5.3, press(disponible=False), [])
    assert v == ["sancionado o no disponible según la prensa"]


def test_a_fit_starter_on_the_way_up_has_no_vetoes():
    assert scout.vetoes("ok", 120_000, 1.0, 7, 5.3, press(), []) == []


def test_no_press_entry_is_not_treated_as_dropped_from_the_xi():
    assert scout.vetoes("ok", 120_000, 1.0, 7, 5.3, None, []) == []


def test_press_lists_him_without_odds_while_fit():
    v = scout.vetoes("ok", 120_000, 1.0, 7, 5.3, press(prob=None), [])
    assert v == ["descartado por la prensa sin lesión (¿conflicto/salida?)"]


def test_a_tag_without_odds_reads_as_a_doubt_not_as_dropped_from_the_xi():
    v = scout.vetoes("ok", 120_000, 1.0, 7, 5.3, press(prob=None, lesionado=True), [])
    assert v == ["la prensa lo marca lesionado (sin probabilidad), sin confirmar"]


def test_falling_value_and_low_odds_still_veto():
    v = scout.vetoes("ok", -300_000, -2.5, 0, 0.6, press(prob=10), [])
    assert v == ["cayendo fuerte", "cae sin haber jugado (¿traspaso?)", "titularidad 10%"]


def test_only_the_two_freshest_headlines_make_it_in():
    news = [{"fecha": f"2026-10-0{i}", "titular": f"titular {i}"} for i in (1, 2, 3)]
    v = scout.vetoes("ok", 120_000, 1.0, 7, 5.3, press(), news)
    assert v == ["noticia 2026-10-01: titular 1", "noticia 2026-10-02: titular 2"]


def test_our_own_injured_player_is_flagged_from_the_api_status():
    from chuleta import cli
    assert cli._squad_warning("injured", press()) == "INJURED"


def test_our_own_player_is_a_doubt_when_only_the_press_knows():
    from chuleta import cli
    assert cli._squad_warning("ok", press(lesionado=True)) == (
        "DUDA: la prensa lo marca lesionado (80% de ser titular), sin confirmar")


def test_a_name_the_press_index_does_not_match_says_nothing():
    from chuleta import cli
    assert cli._squad_warning("ok", None) == ""
    assert cli._squad_warning("ok", press(prob=None)) == ""


def test_a_fit_starter_of_ours_gets_no_warning():
    from chuleta import cli
    assert cli._squad_warning("ok", press()) == ""


def test_the_api_promotes_a_doubt_of_ours_to_an_absence():
    from chuleta import cli
    assert cli._squad_warning("injured", press(lesionado=True)) == "INJURED"


def test_a_system_listing_reports_its_bid_count():
    el = {"discr": "marketPlayerLeague", "numberOfBids": 2}
    assert scout.competition(el) == 2


def test_a_manager_listing_reports_its_offer_count():
    el = {"discr": "marketPlayerTeam", "numberOfOffers": 1}
    assert scout.competition(el) == 1


def test_an_untouched_listing_reports_no_competition():
    assert scout.competition({"discr": "marketPlayerLeague", "numberOfBids": 0}) == 0
    assert scout.competition({"discr": "marketPlayerTeam", "numberOfOffers": 0}) == 0


def test_a_listing_naming_neither_count_is_read_as_untouched():
    assert scout.competition({"discr": "marketPlayerLeague"}) == 0


class FakeClient:
    def __init__(self, market):
        self._market = market

    def market(self, league_id):
        return self._market

    def value_history(self, player_id):
        return []

    def player(self, player_id):
        return {"playerStats": [{"weekNumber": 1, "stats": {"mins_played": [90]}}],
                "averagePoints": 5.3, "team": {"name": "Real Betis"}}


def test_blank_club_odds_are_read_from_the_player_page_before_vetoing(monkeypatch):
    from chuleta import http
    from test_press_condition import PLAYER_PAGE

    blank = {"slug": "pablo-fornals", "nombre": "pablo fornals", "equipo": "betis",
             "prob": None, "lesionado": False, "disponible": True}
    monkeypatch.setattr(scout, "probable_lineups", lambda: {"pablo fornals": blank})
    monkeypatch.setattr(scout, "club_slugs", lambda: ["betis"])
    monkeypatch.setattr(scout, "club_names", lambda client: {"5": "Real Betis"})
    monkeypatch.setattr(scout, "bad_news_for", lambda *a: [])
    monkeypatch.setattr(scout, "last_season_points", lambda *a: None)
    monkeypatch.setattr(http, "cached", lambda key, ttl, producer: producer())
    monkeypatch.setattr(http, "get_text", lambda url, **kw: PLAYER_PAGE)
    market = [{"id": "1", "playerMaster": {"id": "p1", "nickname": "Fornals", "name": "Pablo Fornals Malla",
                                           "teamId": "5", "positionId": 3, "marketValue": 58_000_000,
                                           "playerStatus": "ok"}}]

    row = scout.study(FakeClient(market), "league")[0]

    assert row["prob"] == 80
    assert row["vetos"] == []


def test_my_own_listings_are_not_offered_back_to_me(monkeypatch):
    monkeypatch.setattr(scout, "probable_lineups", lambda: {})
    monkeypatch.setattr(scout, "club_slugs", lambda: [])
    monkeypatch.setattr(scout, "club_names", lambda client: {})
    monkeypatch.setattr(scout, "last_season_points", lambda *a: None)
    pm = {"id": "p1", "nickname": "Fornals", "name": "Pablo Fornals", "teamId": "5", "positionId": 3,
          "marketValue": 58_000_000, "playerStatus": "ok"}
    mine = {"id": "1", "playerMaster": pm, "playerTeam": {"manager": {"id": "42", "managerName": "Keralin"}}}
    theirs = {"id": "2", "playerMaster": {**pm, "id": "p2", "nickname": "Otro"},
              "playerTeam": {"manager": {"id": "7", "managerName": "Rival"}}}

    rows = scout.study(FakeClient([mine, theirs]), "league", my_user_id=42)

    assert [r["nombre"] for r in rows] == ["Otro"]
