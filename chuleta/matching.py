"""Match player names across the API (nicknames like "Rafita") and the press
(full names like "rafa garrido"), accents and word order aside."""

import unicodedata

POS = {1: "POR", 2: "DEF", 3: "MED", 4: "DEL"}


def normalize(name):
    text = unicodedata.normalize("NFKD", name or "")
    return "".join(c for c in text if not unicodedata.combining(c)).lower().strip()


def index_by_name(items, key="nombre"):
    return {normalize(it[key]): it for it in items}


def _word_match(token, words):
    """Whole word, or substring / prefix between long enough words so that
    'Oskarsson' meets 'skarsson' and 'rafa' meets 'rafael', while a short
    'Oso' never matches inside 'cardoso'."""
    for w in words:
        if token == w:
            return True
        if len(token) >= 5 and len(w) >= 5 and (token in w or w in token):
            return True
        if len(token) >= 4 and len(w) >= 4 and (w.startswith(token) or token.startswith(w)):
            return True
    return False


def match_name(nickname, full_name, index):
    """Entry of `index` for an API player, or None. Exact nickname or full
    name first; then every nickname word must match a key word (unique hit
    only); then every key word must match a word of the full name."""
    nick, full = normalize(nickname), normalize(full_name)
    if nick in index:
        return index[nick]
    if full in index:
        return index[full]
    tokens = [t for t in nick.split() if len(t) > 2]
    if tokens:
        hits = [v for k, v in index.items() if all(_word_match(t, k.split()) for t in tokens)]
        if len(hits) == 1:
            return hits[0]
    words = full.split()
    if words:
        for k, v in index.items():
            kw = [t for t in k.split() if len(t) > 2]
            if kw and all(_word_match(t, words) for t in kw):
                return v
    return None
