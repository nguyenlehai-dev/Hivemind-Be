import pytest


@pytest.mark.asyncio
async def test_apps_crud_and_run(client, monkeypatch):
    from app.core import config

    monkeypatch.setattr(config.settings, "runway_backend", "mock")

    # Empty list initially
    r = await client.get("/api/runway/apps")
    assert r.status_code == 200
    assert r.json()["data"] == []

    # Create
    r = await client.post(
        "/api/runway/apps",
        json={
            "name": "Cinematic portrait",
            "description": "16:9, dramatic lighting",
            "mode": "image",
            "model_id": "gen-4",
            "prompt": "cinematic portrait, dramatic lighting",
            "settings": {
                "aspect_ratio": "16:9",
                "num_outputs": 1,
                "seed": 42,
            },
        },
    )
    assert r.status_code == 200
    app = r.json()["data"]
    assert app["id"].startswith("app_")
    assert app["name"] == "Cinematic portrait"
    app_id = app["id"]

    # List should contain it
    r = await client.get("/api/runway/apps")
    assert len(r.json()["data"]) == 1

    # Get
    r = await client.get(f"/api/runway/apps/{app_id}")
    assert r.status_code == 200
    assert r.json()["data"]["settings"]["seed"] == 42

    # Run → should create a generation with preset applied
    r = await client.post(f"/api/runway/apps/{app_id}/run", json={})
    assert r.status_code == 200
    job = r.json()["data"]
    assert job["status"] == "queued"
    assert job["job_id"].startswith("job_")

    # Generation detail picks up the saved preset
    r = await client.get(f"/api/runway/generations/{job['job_id']}")
    detail = r.json()["data"]
    assert detail["model_id"] == "gen-4"
    assert detail["prompt"] == "cinematic portrait, dramatic lighting"
    assert detail["settings"]["seed"] == 42

    # Run with override
    r = await client.post(
        f"/api/runway/apps/{app_id}/run",
        json={"prompt": "different prompt"},
    )
    job2 = r.json()["data"]
    r = await client.get(f"/api/runway/generations/{job2['job_id']}")
    assert r.json()["data"]["prompt"] == "different prompt"

    # Delete
    r = await client.delete(f"/api/runway/apps/{app_id}")
    assert r.status_code == 204

    r = await client.get(f"/api/runway/apps/{app_id}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_run_unknown_app(client):
    r = await client.post("/api/runway/apps/nonexistent/run", json={})
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "app_not_found"


@pytest.mark.asyncio
async def test_app_update_partial(client):
    r = await client.post(
        "/api/runway/apps",
        json={
            "name": "v1",
            "mode": "image",
            "model_id": "gen-4",
            "prompt": "original",
        },
    )
    app_id = r.json()["data"]["id"]

    r = await client.patch(
        f"/api/runway/apps/{app_id}",
        json={"name": "v2", "prompt": "updated prompt"},
    )
    assert r.status_code == 200
    app = r.json()["data"]
    assert app["name"] == "v2"
    assert app["prompt"] == "updated prompt"
    assert app["model_id"] == "gen-4"

    r = await client.patch(
        f"/api/runway/apps/{app_id}",
        json={"settings": {"aspect_ratio": "1:1", "num_outputs": 2, "seed": 7}},
    )
    assert r.json()["data"]["settings"]["seed"] == 7


@pytest.mark.asyncio
async def test_app_update_unknown(client):
    r = await client.patch("/api/runway/apps/nonexistent", json={"name": "x"})
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "app_not_found"
