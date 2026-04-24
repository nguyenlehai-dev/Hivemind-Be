from fastapi import APIRouter, Depends

from app.modules.runway.dependencies import get_generation_service
from app.modules.runway.schemas import (
    GenerateRequest,
    GenerateResponse,
    GenerationDetailResponse,
    GenerationListResponse,
)
from app.modules.runway.services.generation import GenerationService

router = APIRouter(prefix="/generations")


@router.post("", response_model=GenerateResponse)
async def create_generation(
    payload: GenerateRequest,
    service: GenerationService = Depends(get_generation_service),
) -> GenerateResponse:
    return await service.create(payload)


@router.get("", response_model=GenerationListResponse)
async def list_generations(
    service: GenerationService = Depends(get_generation_service),
) -> GenerationListResponse:
    return await service.list()


@router.get("/{job_id}", response_model=GenerationDetailResponse)
async def get_generation(
    job_id: str,
    service: GenerationService = Depends(get_generation_service),
) -> GenerationDetailResponse:
    return await service.get(job_id)


@router.delete("/{job_id}", status_code=204)
async def cancel_or_delete_generation(
    job_id: str,
    service: GenerationService = Depends(get_generation_service),
) -> None:
    """Hybrid: cancels in-progress jobs, deletes terminal rows."""
    await service.cancel(job_id)


@router.post("/{job_id}/retry", response_model=GenerateResponse)
async def retry_generation(
    job_id: str,
    service: GenerationService = Depends(get_generation_service),
) -> GenerateResponse:
    return await service.retry(job_id)
