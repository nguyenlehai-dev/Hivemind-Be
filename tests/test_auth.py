import pytest


@pytest.mark.asyncio
async def test_status_disconnected_initially(client):
    r = await client.get("/api/runway/auth/status")
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["status"] == "disconnected"
    assert body["session_id"] is None


@pytest.mark.asyncio
async def test_mock_login_creates_session(client, monkeypatch):
    # Ensure mock path is used
    from app.core import config

    monkeypatch.setattr(config.settings, "runway_mock_mode", True)

    r = await client.post(
        "/api/runway/auth/login",
        json={"email": "user@test.com", "password": "x"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["status"] == "connected"
    assert body["session_id"].startswith("rw_session_")
    assert body["email"] == "user@test.com"

    # Status now reflects it
    r = await client.get("/api/runway/auth/status")
    assert r.json()["status"] == "connected"
    assert r.json()["email"] == "user@test.com"


@pytest.mark.asyncio
async def test_verify_otp_unknown_session(client):
    r = await client.post(
        "/api/runway/auth/verify-otp",
        json={"session_id": "nope", "otp_code": "1234"},
    )
    # Preserved contract: 200 with status="error" (not 404)
    assert r.status_code == 200
    assert r.json()["status"] == "error"


@pytest.mark.asyncio
async def test_disconnect_clears_session(client, monkeypatch):
    from app.core import config

    monkeypatch.setattr(config.settings, "runway_mock_mode", True)

    # Login first
    await client.post(
        "/api/runway/auth/login",
        json={"email": "z@z.com", "password": "x"},
    )
    assert (await client.get("/api/runway/auth/status")).json()["status"] == "connected"

    r = await client.post("/api/runway/auth/disconnect")
    assert r.status_code == 200
    assert r.json()["status"] == "disconnected"

    # Status now reads disconnected
    assert (
        await client.get("/api/runway/auth/status")
    ).json()["status"] == "disconnected"
