from fastapi import APIRouter, Depends

from app.core.config import settings
from app.modules.runway.clients.runway_api import RunwayAPIClient
from app.modules.runway.dependencies import get_runway_api_client
from app.modules.runway.schemas import CapabilitiesData, CapabilitiesResponse

router = APIRouter()


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
        requires_ref: list[str] = []
    else:
        real_modes = []
        requires_ref = ["video"]

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
