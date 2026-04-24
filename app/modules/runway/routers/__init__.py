from fastapi import APIRouter

from app.modules.runway.routers.apps import router as apps_router
from app.modules.runway.routers.assets import router as assets_router
from app.modules.runway.routers.auth import router as auth_router
from app.modules.runway.routers.capabilities import router as capabilities_router
from app.modules.runway.routers.generations import router as generations_router
from app.modules.runway.routers.models import router as models_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(capabilities_router)
router.include_router(models_router)
router.include_router(assets_router)
router.include_router(generations_router)
router.include_router(apps_router)

__all__ = ["router"]
