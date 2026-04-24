from fastapi import APIRouter, Depends

from app.modules.runway.dependencies import get_app_service
from app.modules.runway.schemas import (
    AppCreateRequest,
    AppListResponse,
    AppResponse,
    AppRunRequest,
    AppRunResponse,
    AppUpdateRequest,
)
from app.modules.runway.services.app import AppService

router = APIRouter(prefix="/apps")


@router.post("", response_model=AppResponse)
async def create_app(
    payload: AppCreateRequest,
    service: AppService = Depends(get_app_service),
) -> AppResponse:
    return await service.create(payload)


@router.get("", response_model=AppListResponse)
async def list_apps(
    service: AppService = Depends(get_app_service),
) -> AppListResponse:
    return await service.list()


@router.get("/{app_id}", response_model=AppResponse)
async def get_app(
    app_id: str,
    service: AppService = Depends(get_app_service),
) -> AppResponse:
    return await service.get(app_id)


@router.patch("/{app_id}", response_model=AppResponse)
async def update_app(
    app_id: str,
    payload: AppUpdateRequest,
    service: AppService = Depends(get_app_service),
) -> AppResponse:
    return await service.update(app_id, payload)


@router.delete("/{app_id}", status_code=204)
async def delete_app(
    app_id: str,
    service: AppService = Depends(get_app_service),
) -> None:
    await service.delete(app_id)


@router.post("/{app_id}/run", response_model=AppRunResponse)
async def run_app(
    app_id: str,
    payload: AppRunRequest,
    service: AppService = Depends(get_app_service),
) -> AppRunResponse:
    return await service.run(app_id, payload)
