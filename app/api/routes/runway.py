from fastapi import APIRouter, File, HTTPException, UploadFile

from app.schemas.runway import (
    AssetUploadResponse,
    AuthLoginRequest,
    AuthResponse,
    AuthStatusResponse,
    GenerateRequest,
    GenerateResponse,
    GenerationDetailResponse,
    ModelCatalogResponse,
    OtpVerifyRequest,
)
from app.services.runway.asset_service import asset_service
from app.services.runway.auth_service import auth_service
from app.services.runway.generation_service import generation_service
from app.services.runway.model_service import model_service

router = APIRouter()


@router.get("/auth/status", response_model=AuthStatusResponse)
def get_auth_status() -> AuthStatusResponse:
    return auth_service.get_status()


@router.post("/auth/login", response_model=AuthResponse)
def login(payload: AuthLoginRequest) -> AuthResponse:
    return auth_service.login(payload)


@router.post("/auth/verify-otp", response_model=AuthResponse)
def verify_otp(payload: OtpVerifyRequest) -> AuthResponse:
    return auth_service.verify_otp(payload)


@router.get("/models", response_model=ModelCatalogResponse)
def get_models(mode: str = "image") -> ModelCatalogResponse:
    return model_service.get_models(mode=mode)


@router.post("/assets/upload", response_model=AssetUploadResponse)
async def upload_asset(file: UploadFile = File(...)) -> AssetUploadResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing file name")
    return await asset_service.upload(file)


@router.post("/generations", response_model=GenerateResponse)
def create_generation(payload: GenerateRequest) -> GenerateResponse:
    return generation_service.create(payload)


@router.get("/generations/{job_id}", response_model=GenerationDetailResponse)
def get_generation(job_id: str) -> GenerationDetailResponse:
    return generation_service.get(job_id)
