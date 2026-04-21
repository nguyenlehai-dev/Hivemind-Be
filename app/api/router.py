from fastapi import APIRouter

from app.modules.runway import router as runway_router

api_router = APIRouter()
api_router.include_router(runway_router, prefix="/api/runway", tags=["runway"])
