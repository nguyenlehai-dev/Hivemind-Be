from app.core.config import settings
from app.core.exceptions import BadRequest
from app.core.ids import generate_id
from app.modules.runway.orm import SessionRow
from app.modules.runway.repositories import SessionRepository
from app.modules.runway.schemas import AuthLoginRequest
from app.modules.runway.services.playwright_login import (
    PlaywrightLoginError,
    PlaywrightLoginService,
)


class LoginService:
    def __init__(
        self,
        sessions: SessionRepository,
        playwright: PlaywrightLoginService | None = None,
    ) -> None:
        self._sessions = sessions
        self._playwright = playwright or PlaywrightLoginService()

    async def login(self, payload: AuthLoginRequest) -> SessionRow:
        if settings.runway_mock_mode:
            return await self._mock_login(payload)
        return await self._playwright_login(payload)

    async def _mock_login(self, payload: AuthLoginRequest) -> SessionRow:
        row = SessionRow(
            session_id=generate_id("rw_session"),
            email=payload.email,
            status="connected",
        )
        return await self._sessions.add(row)

    async def _playwright_login(self, payload: AuthLoginRequest) -> SessionRow:
        # The FE passes user-entered email/password. If the backend has
        # RUNWAY_EMAIL/PASSWORD in env, those win (safer for shared instances
        # where FE should not know real creds). Otherwise use what FE sent.
        email = settings.runway_email or payload.email
        password = settings.runway_password or payload.password

        try:
            result = await self._playwright.login(email, password)
        except PlaywrightLoginError as exc:
            row = SessionRow(
                session_id=generate_id("rw_session"),
                email=email,
                status="error",
                error=str(exc),
            )
            await self._sessions.add(row)
            raise BadRequest(str(exc), code="runway_login_failed") from exc

        row = SessionRow(
            session_id=generate_id("rw_session"),
            email=email,
            status="connected",
            storage_state=result.storage_state,
        )
        return await self._sessions.add(row)
