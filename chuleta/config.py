"""Endpoints, OAuth constants and paths. Secrets never live here."""

import os

API = "https://fantasy-api.llt-services.com/api"
COMPETITION = "1"  # LaLiga
LEGACY_PLAYERS = "https://api-fantasy.llt-services.com/api/v5/players?x-lang=es"  # frozen at 25/26

B2C = "https://login.laliga.es/laligadspprob2c.onmicrosoft.com/oauth2/v2.0"
B2C_POLICY = "B2C_1A_5ULAIP_PARAMETRIZED_SIGNIN"
CLIENT_ID = "af88bcff-1157-40a0-b579-030728aacf0b"
REDIRECT_URI = "authredirect://com.lfp.laligafantasy"
SCOPE = "openid offline_access"

FF = "https://www.futbolfantasy.com"
FF_LINEUPS = f"{FF}/laliga/posibles-alineaciones"
FF_TEAM = f"{FF}/laliga/equipos/{{slug}}"

USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

HOME = os.path.expanduser(os.environ.get("CHULETA_HOME") or "~/.chuleta")
os.makedirs(HOME, exist_ok=True)
TOKENS = os.path.join(HOME, "tokens.json")
PKCE = os.path.join(HOME, "pkce.json")
CACHE = os.path.join(HOME, "cache")
STATE = os.path.join(HOME, "state")
LEAGUE = os.environ.get("CHULETA_LEAGUE")  # pin a league id; default: the account's first
