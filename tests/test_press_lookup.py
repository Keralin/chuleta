from chuleta.sources.press import entry_for


def entry(nombre, equipo, prob):
    return {"slug": nombre.replace(" ", "-"), "nombre": nombre, "equipo": equipo, "prob": prob,
            "lesionado": False, "disponible": True}


PRESS = {"gonzalo villar": entry("gonzalo villar", "elche", 80),
         "ferran jutgla": entry("ferran jutgla", "celta", 50),
         "ferran torres": entry("ferran torres", "barcelona", 60),
         "jude bellingham": entry("jude bellingham", "real-madrid", 90)}


def test_a_namesake_at_another_club_is_not_borrowed():
    assert entry_for(PRESS, "Gonzalo", "Gonzalo García Torres", "Real Madrid") is None


def test_the_player_is_found_inside_his_own_club():
    assert entry_for(PRESS, "Gonzalo", "Gonzalo Villar del Fraile", "Elche CF")["prob"] == 80
    assert entry_for(PRESS, "Ferran", "Ferran Torres García", "FC Barcelona")["prob"] == 60


def test_an_unknown_club_falls_back_to_the_whole_index():
    assert entry_for(PRESS, "Gonzalo", "Gonzalo Villar del Fraile", "?99")["prob"] == 80
    assert entry_for(PRESS, "Gonzalo", "Gonzalo Villar del Fraile", None)["prob"] == 80
