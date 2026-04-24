from fastapi import APIRouter, Depends, File, UploadFile

from app.modules.runway.dependencies import get_asset_service
from app.modules.runway.schemas import AssetUploadResponse
from app.modules.runway.services.asset import AssetService

router = APIRouter(prefix="/assets")


@router.post("/upload", response_model=AssetUploadResponse)
async def upload_asset(
    file: UploadFile = File(...),
    service: AssetService = Depends(get_asset_service),
) -> AssetUploadResponse:
    return await service.upload(file)
