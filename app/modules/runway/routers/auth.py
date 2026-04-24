from fastapi import APIRouter, Depends

from app.modules.runway.dependencies import get_auth_service
from app.modules.runway.schemas import (
    AuthLoginRequest,
    AuthResponse,
    AuthStatusResponse,
    OtpVerifyRequest,
)
from app.modules.runway.services.auth import AuthService

router = APIRouter(prefix="/auth")


@router.get("/status", response_model=AuthStatusResponse)
async def get_auth_status(
    service: AuthService = Depends(get_auth_service),
) -> AuthStatusResponse:
    return await service.get_status()


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: AuthLoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> AuthResponse:
    return await service.login(payload)


@router.post("/verify-otp", response_model=AuthResponse)
async def verify_otp(
    payload: OtpVerifyRequest,
    service: AuthService = Depends(get_auth_service),
) -> AuthResponse:
    return await service.verify_otp(payload)


@router.post("/disconnect", response_model=AuthStatusResponse)
async def disconnect(
    service: AuthService = Depends(get_auth_service),
) -> AuthStatusResponse:
    return await service.disconnect()
