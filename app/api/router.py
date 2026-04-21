from fastapi import APIRouter

from app.api.routes.runway import router as runway_router

api_router = APIRouter()
api_router.include_router(runway_router, prefix="/api/runway", tags=["runway"])
