import base64
from uuid import uuid4

from fastapi import UploadFile

from app.schemas.runway import AssetResponseData, AssetUploadResponse
from app.services.runway.store import AssetState, assets


class RunwayAssetService:
    async def upload(self, file: UploadFile) -> AssetUploadResponse:
        asset_id = f"asset_{uuid4().hex[:10]}"
        content = await file.read()
        encoded = base64.b64encode(content).decode("utf-8")
        content_type = file.content_type or "image/png"
        preview_url = f"data:{content_type};base64,{encoded}"

        assets[asset_id] = AssetState(
            asset_id=asset_id,
            name=file.filename or asset_id,
            preview_url=preview_url,
        )

        return AssetUploadResponse(
            data=AssetResponseData(
                asset_id=asset_id,
                preview_url=preview_url,
            )
        )


asset_service = RunwayAssetService()
