import pytest


@pytest.mark.asyncio
async def test_capabilities_default_mock(client, monkeypatch):
    from app.core import config

    monkeypatch.setattr(config.settings, "runway_backend", "mock")
    monkeypatch.setattr(config.settings, "runway_api_key", "")
    monkeypatch.setattr(config.settings, "runway_team_slug", "")

    r = await client.get("/api/runway/capabilities")
    assert r.status_code == 200
    body = r.json()["data"]
    assert body["backend"] == "mock"
    assert body["runway_api_configured"] is False
    assert body["scraper_ready"] is False
    assert body["real_generation_modes"] == []


@pytest.mark.asyncio
async def test_capabilities_api_configured(client, monkeypatch):
    from app.core import config

    monkeypatch.setattr(config.settings, "runway_backend", "api")
    monkeypatch.setattr(config.settings, "runway_api_key", "key_test_123")

    r = await client.get("/api/runway/capabilities")
    body = r.json()["data"]
    assert body["backend"] == "api"
    assert body["runway_api_configured"] is True
    assert body["real_generation_modes"] == ["video"]
