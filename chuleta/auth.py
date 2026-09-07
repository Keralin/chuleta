"""Login against LaLiga's Azure B2C with an authorization code + PKCE.

The game only offers social logins, so the flow is: print an authorize URL,
the user signs in with Google in a browser, copies the `authredirect://...`
URL the browser fails to open, and we swap its code for tokens. The refresh
token lasts about 90 days.
"""

import base64
import hashlib
import json
import os
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request

from . import config


class AuthError(Exception):
    pass


def _b64(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def jwt_exp(token):
    try:
        payload = token.split(".")[1]
        return json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))).get("exp")
    except Exception:
        return None


def load_tokens():
    try:
        with open(config.TOKENS, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise AuthError("No session. Run `chuleta login` first.") from None


def save_tokens(tokens):
    with open(config.TOKENS, "w", encoding="utf-8") as f:
        json.dump(tokens, f, indent=2)
    os.chmod(config.TOKENS, 0o600)


def bearer(tokens):
    token = tokens.get("access_token") or tokens.get("id_token")
    if not token:
        raise AuthError("Stored session has no usable token. Run `chuleta login`.")
    return token


def expiring(tokens, margin=120):
    exp = jwt_exp(bearer(tokens))
    return exp is not None and time.time() > exp - margin


def start_login():
    """Writes the PKCE verifier to disk and returns the URL to open."""
    verifier = _b64(secrets.token_bytes(64))
    challenge = _b64(hashlib.sha256(verifier.encode()).digest())
    state = secrets.token_urlsafe(16)
    with open(config.PKCE, "w", encoding="utf-8") as f:
        json.dump({"verifier": verifier, "state": state}, f)
    q = urllib.parse.urlencode({
        "p": config.B2C_POLICY, "client_id": config.CLIENT_ID, "response_type": "code",
        "redirect_uri": config.REDIRECT_URI, "scope": config.SCOPE,
        "code_challenge": challenge, "code_challenge_method": "S256",
        "state": state, "nonce": state,
    })
    return f"{config.B2C}/authorize?{q}"


def _token_request(form):
    data = urllib.parse.urlencode(form).encode()
    req = urllib.request.Request(f"{config.B2C}/token?p={config.B2C_POLICY}", data=data, method="POST",
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        if "invalid_grant" in detail or "AADB2C90090" in detail:
            raise AuthError("The code or session was rejected: codes are single-use and expire in "
                            "minutes. Run `chuleta login` again and paste the redirect URL right away.")
        raise AuthError(f"token endpoint {e.code}: {detail[:200]}")


def finish_login(pasted):
    """Swaps the code in the pasted redirect URL for tokens and stores them."""
    try:
        with open(config.PKCE, encoding="utf-8") as f:
            pkce = json.load(f)
    except FileNotFoundError:
        raise AuthError("Run `chuleta login` without arguments first.") from None
    pasted = pasted.strip().strip("'\"")
    code = urllib.parse.parse_qs(pasted.split("?", 1)[1]).get("code", [pasted])[0] if "code=" in pasted else pasted
    tokens = _token_request({
        "grant_type": "authorization_code", "client_id": config.CLIENT_ID, "code": code,
        "redirect_uri": config.REDIRECT_URI, "code_verifier": pkce["verifier"], "scope": config.SCOPE,
    })
    save_tokens(tokens)
    os.remove(config.PKCE)
    return tokens


def refresh(tokens):
    rt = tokens.get("refresh_token")
    if not rt:
        raise AuthError("No refresh token stored. Run `chuleta login`.")
    fresh = _token_request({"grant_type": "refresh_token", "refresh_token": rt,
                            "client_id": config.CLIENT_ID, "scope": config.SCOPE})
    fresh.setdefault("refresh_token", rt)
    save_tokens(fresh)
    return fresh
