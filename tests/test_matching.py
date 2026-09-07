from chuleta.matching import index_by_name, match_name


def idx(*names):
    return index_by_name([{"nombre": n, "v": n} for n in names])


def test_short_token_needs_a_whole_word():
    assert match_name("Oso", "", idx("johnny cardoso")) is None
    assert match_name("Oso", "", idx("joaquin oso"))["v"] == "joaquin oso"


def test_long_tokens_match_by_substring():
    assert match_name("Oskarsson", "", idx("orri steinn skarsson"))["v"] == "orri steinn skarsson"


def test_ambiguous_nickname_is_rejected():
    assert match_name("Pedro", "", idx("pedro porro", "pedro leon")) is None


def test_press_key_matches_full_name_with_prefix():
    assert match_name("Rafita", "Rafael Garrido Hierro", idx("rafa garrido"))["v"] == "rafa garrido"
