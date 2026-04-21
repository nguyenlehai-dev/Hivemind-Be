from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.modules.runway.clients.runway_api import RunwayAPIClient
from app.modules.runway.repositories import (
    AppRepository,
    AssetRepository,
    GenerationRepository,
    SessionRepository,
)
from app.modules.runway.services.app import AppService
from app.modules.runway.services.asset import AssetService
from app.modules.runway.services.auth import AuthService
from app.modules.runway.services.generation import GenerationService
from app.modules.runway.services.login import LoginService
from app.modules.runway.services.model import ModelService
from app.modules.runway.services.runway_scraper import RunwayScraperService


def get_runway_api_client() -> RunwayAPIClient:
    return RunwayAPIClient()


def get_runway_scraper() -> RunwayScraperService:
    return RunwayScraperService()


def get_session_repository(
    db: AsyncSession = Depends(get_db_session),
) -> SessionRepository:
    return SessionRepository(db)


def get_asset_repository(
    db: AsyncSession = Depends(get_db_session),
) -> AssetRepository:
    return AssetRepository(db)


def get_generation_repository(
    db: AsyncSession = Depends(get_db_session),
) -> GenerationRepository:
    return GenerationRepository(db)


def get_app_repository(
    db: AsyncSession = Depends(get_db_session),
) -> AppRepository:
    return AppRepository(db)


def get_login_service(
    sessions: SessionRepository = Depends(get_session_repository),
) -> LoginService:
    return LoginService(sessions)


def get_auth_service(
    sessions: SessionRepository = Depends(get_session_repository),
    login: LoginService = Depends(get_login_service),
) -> AuthService:
    return AuthService(sessions, login)


def get_asset_service(
    assets: AssetRepository = Depends(get_asset_repository),
) -> AssetService:
    return AssetService(assets)


def get_generation_service(
    generations: GenerationRepository = Depends(get_generation_repository),
    assets: AssetRepository = Depends(get_asset_repository),
    sessions: SessionRepository = Depends(get_session_repository),
    runway_api: RunwayAPIClient = Depends(get_runway_api_client),
    scraper: RunwayScraperService = Depends(get_runway_scraper),
) -> GenerationService:
    return GenerationService(generations, assets, sessions, runway_api, scraper)


def get_model_service() -> ModelService:
    return ModelService()


def get_app_service(
    apps: AppRepository = Depends(get_app_repository),
    generations: GenerationService = Depends(get_generation_service),
) -> AppService:
    return AppService(apps, generations)
