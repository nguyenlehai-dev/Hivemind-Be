from typing import Literal

from pydantic import BaseModel, EmailStr, Field

from app.core.response import Envelope, SuccessModel


class AuthLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class OtpVerifyRequest(BaseModel):
    session_id: str
    otp_code: str = Field(min_length=4, max_length=8)


class AuthResponse(SuccessModel):
    status: Literal["connected", "otp_required", "error"]
    session_id: str | None = None
    email: str | None = None
    message: str | None = None


class AuthStatusResponse(SuccessModel):
    status: Literal["disconnected", "connecting", "connected", "otp_required", "error"]
    session_id: str | None = None
    email: str | None = None


class ModelItem(BaseModel):
    id: str
    name: str
    vendor: str
    media_types: list[str]
    capabilities: list[str]


class ModelCatalogResponse(Envelope[list[ModelItem]]):
    pass


class CapabilitiesData(BaseModel):
    backend: Literal["mock", "api", "scraper"]
    runway_api_configured: bool
    scraper_ready: bool
    real_generation_modes: list[str]
    requires_reference_modes: list[str]
    default_video_model: str


class CapabilitiesResponse(Envelope[CapabilitiesData]):
    pass


class AssetResponseData(BaseModel):
    asset_id: str
    preview_url: str


class AssetUploadResponse(Envelope[AssetResponseData]):
    pass


class ReferenceInput(BaseModel):
    asset_id: str


class GenerationSettings(BaseModel):
    aspect_ratio: str = "16:9"
    num_outputs: int = 1
    seed: int | None = None


class GenerateRequest(BaseModel):
    mode: Literal["image", "video", "audio"]
    model_id: str
    prompt: str = ""
    references: list[ReferenceInput] = []
    settings: GenerationSettings = GenerationSettings()


class GenerateResponseData(BaseModel):
    job_id: str
    status: Literal["queued", "running", "completed", "failed"]


class GenerateResponse(Envelope[GenerateResponseData]):
    pass


class GenerationDetailData(BaseModel):
    id: str
    status: Literal["queued", "running", "completed", "failed"]
    mode: str
    model_id: str
    prompt: str
    result_urls: list[str] = []
    settings: dict = {}
    created_at: str
    error: str | None = None


class GenerationDetailResponse(Envelope[GenerationDetailData]):
    pass


class GenerationListItem(BaseModel):
    id: str
    status: Literal["queued", "running", "completed", "failed"]
    mode: str
    model_id: str
    prompt: str
    result_urls: list[str] = []
    created_at: str


class GenerationListResponse(Envelope[list[GenerationListItem]]):
    pass


# ---- Apps -----------------------------------------------------------------

class AppCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str = ""
    mode: Literal["image", "video", "audio"]
    model_id: str = Field(min_length=1)
    prompt: str = ""
    settings: GenerationSettings = GenerationSettings()


class AppUpdateRequest(BaseModel):
    """All fields optional. Missing fields keep their current value."""

    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = None
    mode: Literal["image", "video", "audio"] | None = None
    model_id: str | None = Field(default=None, min_length=1)
    prompt: str | None = None
    settings: GenerationSettings | None = None


class AppItem(BaseModel):
    id: str
    name: str
    description: str
    mode: Literal["image", "video", "audio"]
    model_id: str
    prompt: str
    settings: dict
    created_at: str


class AppResponse(Envelope[AppItem]):
    pass


class AppListResponse(Envelope[list[AppItem]]):
    pass


class AppRunRequest(BaseModel):
    # Optional overrides at run-time; falls back to app's saved values.
    prompt: str | None = None
    references: list[ReferenceInput] = []


class AppRunResponse(Envelope[GenerateResponseData]):
    pass
