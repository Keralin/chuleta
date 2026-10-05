from chuleta.sources.press import condition


def entry(prob=80, lesionado=False, disponible=True):
    return {"slug": "x", "nombre": "x", "equipo": "y",
            "prob": prob, "lesionado": lesionado, "disponible": disponible}


def test_the_api_status_is_the_only_thing_that_makes_an_absence():
    assert condition(entry(), "injured") == ("out", "estado injured")
    assert condition(None, "doubtful")[0] == "out"


def test_a_suspension_is_an_absence_too():
    assert condition(entry(disponible=False), "ok")[0] == "out"


def test_luismi_cruz_eighty_per_cent_and_tagged_stays_a_doubt():
    # the club had him training apart, but nothing in the press data said so
    fitness, reason = condition(entry(prob=80, lesionado=True), "ok")
    assert fitness == "doubt"
    assert "80% de ser titular" in reason and "sin confirmar" in reason


def test_bellerin_seventy_per_cent_and_tagged_reads_the_same():
    # he was fit and started: the odds cannot tell these two apart, so neither
    # case is promoted to an absence
    assert condition(entry(prob=70, lesionado=True), "ok")[0] == "doubt"


def test_a_tag_without_odds_is_still_only_a_doubt():
    fitness, reason = condition(entry(prob=None, lesionado=True), "ok")
    assert fitness == "doubt" and "sin probabilidad" in reason


def test_a_fit_starter_is_fit():
    assert condition(entry(), "ok") == ("fit", "")


def test_no_press_entry_is_not_a_doubt():
    assert condition(None, "ok") == ("fit", "")
    assert condition({}, "ok") == ("fit", "")


def test_the_api_wins_over_a_press_tag_so_the_reason_is_not_doubled():
    assert condition(entry(lesionado=True), "injured") == ("out", "estado injured")
