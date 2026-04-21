from fastapi import APIRouter, Depends, File, UploadFile

from app.core.config import settings
from app.modules.runway.clients.runway_api import RunwayAPIClient
from app.modules.runway.dependencies import (
    get_app_service,
    get_asset_service,
    get_auth_service,
    get_generation_service,
    get_model_service,
    get_runway_api_client,
)
from app.modules.runway.schemas import (
    AppCreateRequest,
    AppListResponse,
    AppResponse,
    AppRunRequest,
    AppRunResponse,
    AppUpdateRequest,
    AssetUploadResponse,
    AuthLoginRequest,
    AuthResponse,
    AuthStatusResponse,
    CapabilitiesData,
    CapabilitiesResponse,
    GenerateRequest,
    GenerateResponse,
    GenerationDetailResponse,
    GenerationListResponse,
    ModelCatalogResponse,
    OtpVerifyRequest,
)
from app.modules.runway.services.app import AppService
from app.modules.runway.services.asset import AssetService
from app.modules.runway.services.auth import AuthService
from app.modules.runway.services.generation import GenerationService
from app.modules.runway.services.model import ModelService

router = APIRouter()


@router.get("/auth/status", response_model=AuthStatusResponse)
async def get_auth_status(
    service: AuthService = Depends(get_auth_service),
) -> AuthStatusResponse:
    return await service.get_status()


@router.post("/auth/login", response_model=AuthResponse)
async def login(
    payload: AuthLoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> AuthResponse:
    return await service.login(payload)


@router.post("/auth/verify-otp", response_model=AuthResponse)
async def verify_otp(
    payload: OtpVerifyRequest,
    service: AuthService = Depends(get_auth_service),
) -> AuthResponse:
    return await service.verify_otp(payload)


@router.post("/auth/disconnect", response_model=AuthStatusResponse)
async def disconnect(
    service: AuthService = Depends(get_auth_service),
) -> AuthStatusResponse:
    return await service.disconnect()


@router.get("/capabilities", response_model=CapabilitiesResponse)
def get_capabilities(
    runway_api: RunwayAPIClient = Depends(get_runway_api_client),
) -> CapabilitiesResponse:
    backend = settings.runway_backend.lower()
    scraper_ready = bool(settings.runway_team_slug)

    if backend == "api" and runway_api.is_configured:
        real_modes = ["video"]
        requires_ref = ["video"]
    elif backend == "scraper" and scraper_ready:
        real_modes = ["image", "video"]
        requires_ref: list[str] = []  # scraper allows text-only too
    else:
        real_modes = []
        requires_ref = ["video"]  # keep FE hint for API path

    return CapabilitiesResponse(
        data=CapabilitiesData(
            backend=backend if backend in ("mock", "api", "scraper") else "mock",
            runway_api_configured=runway_api.is_configured,
            scraper_ready=scraper_ready,
            real_generation_modes=real_modes,
            requires_reference_modes=requires_ref,
            default_video_model=settings.runway_default_video_model,
        ),
    )


@router.get("/models", response_model=ModelCatalogResponse)
def get_models(
    mode: str = "image",
    service: ModelService = Depends(get_model_service),
) -> ModelCatalogResponse:
    return service.get_models(mode=mode)


@router.post("/assets/upload", response_model=AssetUploadResponse)
async def upload_asset(
    file: UploadFile = File(...),
    service: AssetService = Depends(get_asset_service),
) -> AssetUploadResponse:
    return await service.upload(file)


@router.post("/generations", response_model=GenerateResponse)
async def create_generation(
    payload: GenerateRequest,
    service: GenerationService = Depends(get_generation_service),
) -> GenerateResponse:
    return await service.create(payload)


@router.delete("/generations/{job_id}", status_code=204)
async def cancel_or_delete_generation(
    job_id: str,
    service: GenerationService = Depends(get_generation_service),
) -> None:
    """Hybrid: cancels in-progress jobs, deletes terminal rows."""
    await service.cancel(job_id)


@router.post("/generations/{job_id}/retry", response_model=GenerateResponse)
async def retry_generation(
    job_id: str,
    service: GenerationService = Depends(get_generation_service),
) -> GenerateResponse:
    return await service.retry(job_id)


# ---- Apps -----------------------------------------------------------------


@router.post("/apps", response_model=AppResponse)
async def create_app(
    payload: AppCreateRequest,
    service: AppService = Depends(get_app_service),
) -> AppResponse:
    return await service.create(payload)


@router.get("/apps", response_model=AppListResponse)
async def list_apps(
    service: AppService = Depends(get_app_service),
) -> AppListResponse:
    return await service.list()


@router.get("/apps/{app_id}", response_model=AppResponse)
async def get_app(
    app_id: str,
    service: AppService = Depends(get_app_service),
) -> AppResponse:
    return await service.get(app_id)


@router.patch("/apps/{app_id}", response_model=AppResponse)
async def update_app(
    app_id: str,
    payload: AppUpdateRequest,
    service: AppService = Depends(get_app_service),
) -> AppResponse:
    return await service.update(app_id, payload)


@router.delete("/apps/{app_id}", status_code=204)
async def delete_app(
    app_id: str,
    service: AppService = Depends(get_app_service),
) -> None:
    await service.delete(app_id)


@router.post("/apps/{app_id}/run", response_model=AppRunResponse)
async def run_app(
    app_id: str,
    payload: AppRunRequest,
    service: AppService = Depends(get_app_service),
) -> AppRunResponse:
    return await service.run(app_id, payload)


@router.get("/generations", response_model=GenerationListResponse)
async def list_generations(
    service: GenerationService = Depends(get_generation_service),
) -> GenerationListResponse:
    return await service.list()


@router.get("/generations/{job_id}", response_model=GenerationDetailResponse)
async def get_generation(
    job_id: str,
    service: GenerationService = Depends(get_generation_service),
) -> GenerationDetailResponse:
    return await service.get(job_id)
