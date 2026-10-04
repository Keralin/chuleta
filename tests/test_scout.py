from chuleta.strategy import scout


def press(prob=80, lesionado=False, disponible=True):
    return {"slug": "luismi-cruz", "nombre": "luismi cruz", "equipo": "deportivo",
            "prob": prob, "lesionado": lesionado, "disponible": disponible}


def test_press_injury_vetoes_a_player_the_api_still_calls_ok():
    v = scout.vetoes("ok", 120_000, 1.0, 7, 5.3, press(lesionado=True), [])
    assert v == ["lesionado según la prensa (la API lo da ok)"]


def test_press_injury_does_not_repeat_what_the_api_already_said():
    v = scout.vetoes("injured", 120_000, 1.0, 7, 5.3, press(lesionado=True), [])
    assert v == ["estado injured", "lesionado según la prensa"]


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


def test_an_injured_player_without_odds_reads_as_injured_not_as_dropped():
    v = scout.vetoes("ok", 120_000, 1.0, 7, 5.3, press(prob=None, lesionado=True), [])
    assert v == ["lesionado según la prensa (la API lo da ok)"]


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


def test_our_own_player_is_flagged_when_only_the_press_knows():
    from chuleta import cli
    assert cli._squad_warning("ok", press(lesionado=True)) == "prensa: lesionado"


def test_a_name_the_press_index_does_not_match_says_nothing():
    from chuleta import cli
    assert cli._squad_warning("ok", None) == ""
    assert cli._squad_warning("ok", press(prob=None)) == ""


def test_a_fit_starter_of_ours_gets_no_warning():
    from chuleta import cli
    assert cli._squad_warning("ok", press()) == ""


def test_both_sources_are_reported_when_both_know():
    from chuleta import cli
    assert cli._squad_warning("injured", press(lesionado=True)) == "INJURED, prensa: lesionado"
