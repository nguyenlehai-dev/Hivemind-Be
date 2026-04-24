from fastapi import APIRouter, Depends

from app.modules.runway.dependencies import get_model_service
from app.modules.runway.schemas import ModelCatalogResponse
from app.modules.runway.services.model import ModelService

router = APIRouter()


@router.get("/models", response_model=ModelCatalogResponse)
def get_models(
    mode: str = "image",
    service: ModelService = Depends(get_model_service),
) -> ModelCatalogResponse:
    return service.get_models(mode=mode)
