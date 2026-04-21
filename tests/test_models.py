import pytest


@pytest.mark.asyncio
async def test_models_image_mode(client):
    r = await client.get("/api/runway/models", params={"mode": "image"})
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert len(body["data"]) >= 1
    for item in body["data"]:
        assert "image" in item["media_types"]


@pytest.mark.asyncio
async def test_models_video_mode(client):
    r = await client.get("/api/runway/models", params={"mode": "video"})
    assert r.status_code == 200
    assert all("video" in m["media_types"] for m in r.json()["data"])
