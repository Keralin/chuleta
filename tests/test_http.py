import io
import urllib.error

import pytest

from chuleta import config, http


def test_a_half_written_cache_file_is_rebuilt_not_fatal(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CACHE", str(tmp_path))
    (tmp_path / "k.json").write_text('{"half": ')
    assert http.cached("k", 3600, lambda: {"ok": 1}) == {"ok": 1}
    assert http.cached("k", 3600, lambda: {"other": 2}) == {"ok": 1}


def test_a_client_error_is_raised_at_once_without_retrying(monkeypatch):
    calls = []

    def not_found(req, timeout):
        calls.append(req.full_url)
        raise urllib.error.HTTPError(req.full_url, 404, "Not Found", {}, io.BytesIO(b""))

    monkeypatch.setattr(http.urllib.request, "urlopen", not_found)
    monkeypatch.setattr(http.time, "sleep", lambda s: pytest.fail("a 404 must not back off"))
    with pytest.raises(urllib.error.HTTPError):
        http.get_text("https://example.invalid/x")
    assert len(calls) == 1


def test_rate_limiting_is_backed_off_and_retried(monkeypatch):
    calls = []

    def limited_then_ok(req, timeout):
        calls.append(1)
        if len(calls) == 1:
            raise urllib.error.HTTPError(req.full_url, 429, "Too Many Requests", {}, io.BytesIO(b""))
        return io.BytesIO(b"ok")

    monkeypatch.setattr(http.urllib.request, "urlopen", limited_then_ok)
    monkeypatch.setattr(http.time, "sleep", lambda s: None)
    assert http.get_text("https://example.invalid/x") == "ok"
