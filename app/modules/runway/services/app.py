from app.core.exceptions import EntityNotFound
from app.core.ids import generate_id
from app.modules.runway.orm import AppRow
from app.modules.runway.repositories import AppRepository
from app.modules.runway.schemas import (
    AppCreateRequest,
    AppItem,
    AppListResponse,
    AppResponse,
    AppRunRequest,
    AppRunResponse,
    AppUpdateRequest,
    GenerateRequest,
    GenerationSettings,
)
from app.modules.runway.services.generation import GenerationService


class AppService:
    def __init__(
        self,
        apps: AppRepository,
        generations: GenerationService,
    ) -> None:
        self._apps = apps
        self._generations = generations

    async def create(self, payload: AppCreateRequest) -> AppResponse:
        row = AppRow(
            app_id=generate_id("app"),
            name=payload.name,
            description=payload.description,
            mode=payload.mode,
            model_id=payload.model_id,
            prompt=payload.prompt,
            settings=payload.settings.model_dump(),
        )
        await self._apps.add(row)
        return AppResponse(data=_to_item(row))

    async def get(self, app_id: str) -> AppResponse:
        row = await self._apps.get(app_id)
        if row is None:
            raise EntityNotFound("App not found", code="app_not_found")
        return AppResponse(data=_to_item(row))

    async def list(self) -> AppListResponse:
        rows = await self._apps.list()
        return AppListResponse(data=[_to_item(r) for r in rows])

    async def delete(self, app_id: str) -> None:
        deleted = await self._apps.delete(app_id)
        if not deleted:
            raise EntityNotFound("App not found", code="app_not_found")

    async def update(self, app_id: str, payload: AppUpdateRequest) -> AppResponse:
        row = await self._apps.get(app_id)
        if row is None:
            raise EntityNotFound("App not found", code="app_not_found")

        updates = payload.model_dump(exclude_unset=True)
        if "settings" in updates and updates["settings"] is not None:
            updates["settings"] = updates["settings"]  # already dict from Pydantic
        elif "settings" in updates:
            updates.pop("settings")

        for field, value in updates.items():
            if value is not None:
                setattr(row, field, value)

        return AppResponse(data=_to_item(row))

    async def run(self, app_id: str, payload: AppRunRequest) -> AppRunResponse:
        row = await self._apps.get(app_id)
        if row is None:
            raise EntityNotFound("App not found", code="app_not_found")

        gen_payload = GenerateRequest(
            mode=row.mode,
            model_id=row.model_id,
            prompt=payload.prompt if payload.prompt is not None else row.prompt,
            references=payload.references,
            settings=GenerationSettings(**row.settings) if row.settings else GenerationSettings(),
        )
        gen_response = await self._generations.create(gen_payload)
        return AppRunResponse(data=gen_response.data)


def _to_item(row: AppRow) -> AppItem:
    return AppItem(
        id=row.app_id,
        name=row.name,
        description=row.description,
        mode=row.mode,
        model_id=row.model_id,
        prompt=row.prompt,
        settings=row.settings,
        created_at=row.created_at.isoformat(),
    )
