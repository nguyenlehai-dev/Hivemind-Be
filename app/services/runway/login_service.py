from uuid import uuid4

from app.core.config import settings
from app.schemas.runway import AuthLoginRequest
from app.services.runway.store import SessionState, sessions


class RunwayLoginService:
    def login(self, payload: AuthLoginRequest) -> SessionState:
        if not settings.runway_mock_mode:
            # TODO: Replace mock flow with Playwright-based login and storageState capture.
            raise NotImplementedError("Real Playwright login is not wired yet.")

        session = SessionState(
            session_id=f"rw_session_{uuid4().hex[:10]}",
            email=payload.email,
        )
        sessions[session.session_id] = session
        return session


login_service = RunwayLoginService()
