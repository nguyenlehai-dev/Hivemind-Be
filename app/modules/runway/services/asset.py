import base64

from fastapi import UploadFile

from app.core.exceptions import BadRequest
from app.core.ids import generate_id
from app.modules.runway.orm import AssetRow
from app.modules.runway.repositories import AssetRepository
from app.modules.runway.schemas import AssetResponseData, AssetUploadResponse


class AssetService:
    def __init__(self, assets: AssetRepository) -> None:
        self._assets = assets

    async def upload(self, file: UploadFile) -> AssetUploadResponse:
        if not file.filename:
            raise BadRequest("Missing file name", code="missing_file_name")

        asset_id = generate_id("asset")
        content = await file.read()
        encoded = base64.b64encode(content).decode("utf-8")
        content_type = file.content_type or "image/png"
        preview_url = f"data:{content_type};base64,{encoded}"

        await self._assets.add(
            AssetRow(asset_id=asset_id, name=file.filename, preview_url=preview_url),
        )

        return AssetUploadResponse(
            data=AssetResponseData(asset_id=asset_id, preview_url=preview_url),
        )
