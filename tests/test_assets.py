import pytest


@pytest.mark.asyncio
async def test_asset_upload(client):
    # 1×1 PNG
    png_bytes = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
        "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
    )
    r = await client.post(
        "/api/runway/assets/upload",
        files={"file": ("tiny.png", png_bytes, "image/png")},
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["asset_id"].startswith("asset_")
    assert data["preview_url"].startswith("data:image/png;base64,")


@pytest.mark.asyncio
async def test_asset_upload_no_file(client):
    # Missing the `file` field entirely → FastAPI validation rejects at 422.
    r = await client.post("/api/runway/assets/upload")
    assert r.status_code == 422
