import pytest


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    """Never touch the user's ~/.chuleta during tests."""
    from chuleta import config
    monkeypatch.setattr(config, "HOME", str(tmp_path))
    monkeypatch.setattr(config, "CACHE", str(tmp_path / "cache"))
    monkeypatch.setattr(config, "TOKENS", str(tmp_path / "tokens.json"))
    monkeypatch.setattr(config, "PKCE", str(tmp_path / "pkce.json"))
