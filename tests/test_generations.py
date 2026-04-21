import asyncio

import pytest


@pytest.mark.asyncio
async def test_generation_lifecycle_mock(client, monkeypatch):
    from app.core import config

    monkeypatch.setattr(config.settings, "runway_backend", "mock")

    # Create
    r = await client.post(
        "/api/runway/generations",
        json={
            "mode": "image",
            "model_id": "gen-4",
            "prompt": "hello world",
        },
    )
    assert r.status_code == 200
    created = r.json()["data"]
    assert created["status"] == "queued"
    job_id = created["job_id"]

    # Detail — fresh job, should still be queued or just moved to running
    r = await client.get(f"/api/runway/generations/{job_id}")
    assert r.status_code == 200
    detail = r.json()["data"]
    assert detail["id"] == job_id
    assert detail["mode"] == "image"
    assert detail["model_id"] == "gen-4"
    assert detail["prompt"] == "hello world"

    # Wait for mock timer to advance to "completed"
    await asyncio.sleep(3.2)
    r = await client.get(f"/api/runway/generations/{job_id}")
    detail = r.json()["data"]
    assert detail["status"] == "completed"
    assert len(detail["result_urls"]) == 1
    assert detail["result_urls"][0].startswith("data:image/svg+xml")

    # List includes the job
    r = await client.get("/api/runway/generations")
    assert any(j["id"] == job_id for j in r.json()["data"])


@pytest.mark.asyncio
async def test_generation_404(client):
    r = await client.get("/api/runway/generations/does-not-exist")
    assert r.status_code == 404
    body = r.json()
    assert body["success"] is False
    assert body["error"]["code"] == "job_not_found"


@pytest.mark.asyncio
async def test_generation_cancel_in_progress(client, monkeypatch):
    from app.core import config

    monkeypatch.setattr(config.settings, "runway_backend", "mock")

    r = await client.post(
        "/api/runway/generations",
        json={"mode": "image", "model_id": "gen-4", "prompt": "cancel me"},
    )
    job_id = r.json()["data"]["job_id"]

    # While queued → cancel marks failed, row still exists
    r = await client.delete(f"/api/runway/generations/{job_id}")
    assert r.status_code == 204

    r = await client.get(f"/api/runway/generations/{job_id}")
    detail = r.json()["data"]
    assert detail["status"] == "failed"
    assert "Cancelled" in (detail["error"] or "")


@pytest.mark.asyncio
async def test_generation_delete_terminal_removes_row(client, monkeypatch):
    from app.core import config
    import asyncio

    monkeypatch.setattr(config.settings, "runway_backend", "mock")

    r = await client.post(
        "/api/runway/generations",
        json={"mode": "image", "model_id": "gen-4", "prompt": "done soon"},
    )
    job_id = r.json()["data"]["job_id"]

    # Cancel once → marks failed (terminal)
    await client.delete(f"/api/runway/generations/{job_id}")
    assert (
        await client.get(f"/api/runway/generations/{job_id}")
    ).json()["data"]["status"] == "failed"

    # DELETE again → actually removes from DB
    r = await client.delete(f"/api/runway/generations/{job_id}")
    assert r.status_code == 204

    r = await client.get(f"/api/runway/generations/{job_id}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_generation_retry(client, monkeypatch):
    import asyncio
    from app.core import config

    monkeypatch.setattr(config.settings, "runway_backend", "mock")

    r = await client.post(
        "/api/runway/generations",
        json={
            "mode": "image",
            "model_id": "gen-4",
            "prompt": "retry test",
            "settings": {"aspect_ratio": "1:1", "num_outputs": 1, "seed": 99},
        },
    )
    original_id = r.json()["data"]["job_id"]

    # Cancel to make terminal
    await client.delete(f"/api/runway/generations/{original_id}")

    # Retry → new job with same params
    r = await client.post(f"/api/runway/generations/{original_id}/retry")
    assert r.status_code == 200
    new_id = r.json()["data"]["job_id"]
    assert new_id != original_id

    r = await client.get(f"/api/runway/generations/{new_id}")
    detail = r.json()["data"]
    assert detail["prompt"] == "retry test"
    assert detail["model_id"] == "gen-4"
    assert detail["settings"]["seed"] == 99


@pytest.mark.asyncio
async def test_retry_in_progress_rejected(client, monkeypatch):
    from app.core import config

    monkeypatch.setattr(config.settings, "runway_backend", "mock")

    r = await client.post(
        "/api/runway/generations",
        json={"mode": "image", "model_id": "gen-4", "prompt": "pending"},
    )
    job_id = r.json()["data"]["job_id"]

    r = await client.post(f"/api/runway/generations/{job_id}/retry")
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "job_not_terminal"
