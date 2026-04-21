from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class AuthLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class OtpVerifyRequest(BaseModel):
    session_id: str
    otp_code: str = Field(min_length=4, max_length=8)


class AuthResponse(BaseModel):
    success: bool = True
    status: Literal["connected", "otp_required", "error"]
    session_id: str | None = None
    email: str | None = None
    message: str | None = None


class AuthStatusResponse(BaseModel):
    success: bool = True
    status: Literal["disconnected", "connecting", "connected", "otp_required", "error"]
    session_id: str | None = None
    email: str | None = None


class ModelItem(BaseModel):
    id: str
    name: str
    vendor: str
    media_types: list[str]
    capabilities: list[str]


class ModelCatalogResponse(BaseModel):
    success: bool = True
    data: list[ModelItem]


class AssetResponseData(BaseModel):
    asset_id: str
    preview_url: str


class AssetUploadResponse(BaseModel):
    success: bool = True
    data: AssetResponseData


class ReferenceInput(BaseModel):
    asset_id: str


class GenerationSettings(BaseModel):
    aspect_ratio: str = "16:9"
    num_outputs: int = 1


class GenerateRequest(BaseModel):
    mode: Literal["image", "video", "audio"]
    model_id: str
    prompt: str = ""
    references: list[ReferenceInput] = []
    settings: GenerationSettings = GenerationSettings()


class GenerateResponseData(BaseModel):
    job_id: str
    status: Literal["queued", "running", "completed", "failed"]


class GenerateResponse(BaseModel):
    success: bool = True
    data: GenerateResponseData


class GenerationDetailData(BaseModel):
    id: str
    status: Literal["queued", "running", "completed", "failed"]
    model_id: str
    prompt: str
    result_urls: list[str] = []
    error: str | None = None


class GenerationDetailResponse(BaseModel):
    success: bool = True
    data: GenerationDetailData
