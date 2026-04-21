from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.runway.orm import AppRow, AssetRow, GenerationRow, SessionRow


class SessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, row: SessionRow) -> SessionRow:
        self._session.add(row)
        await self._session.flush()
        return row

    async def get(self, session_id: str) -> SessionRow | None:
        return await self._session.get(SessionRow, session_id)

    async def last(self) -> SessionRow | None:
        stmt = select(SessionRow).order_by(SessionRow.created_at.desc()).limit(1)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def count(self) -> int:
        from sqlalchemy import func

        stmt = select(func.count(SessionRow.session_id))
        return int((await self._session.execute(stmt)).scalar() or 0)

    async def clear_all(self) -> int:
        stmt = delete(SessionRow)
        result = await self._session.execute(stmt)
        return result.rowcount or 0


class AssetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, row: AssetRow) -> AssetRow:
        self._session.add(row)
        await self._session.flush()
        return row

    async def get(self, asset_id: str) -> AssetRow | None:
        return await self._session.get(AssetRow, asset_id)


class GenerationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, row: GenerationRow) -> GenerationRow:
        self._session.add(row)
        await self._session.flush()
        return row

    async def get(self, job_id: str) -> GenerationRow | None:
        return await self._session.get(GenerationRow, job_id)

    async def list(self) -> list[GenerationRow]:
        stmt = select(GenerationRow).order_by(GenerationRow.created_at.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def delete(self, job_id: str) -> bool:
        stmt = delete(GenerationRow).where(GenerationRow.job_id == job_id)
        result = await self._session.execute(stmt)
        return result.rowcount > 0


class AppRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, row: AppRow) -> AppRow:
        self._session.add(row)
        await self._session.flush()
        return row

    async def get(self, app_id: str) -> AppRow | None:
        return await self._session.get(AppRow, app_id)

    async def list(self) -> list[AppRow]:
        stmt = select(AppRow).order_by(AppRow.created_at.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def delete(self, app_id: str) -> bool:
        stmt = delete(AppRow).where(AppRow.app_id == app_id)
        result = await self._session.execute(stmt)
        return result.rowcount > 0
