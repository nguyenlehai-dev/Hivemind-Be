from app.modules.runway.repositories import SessionRepository
from app.modules.runway.schemas import (
    AuthLoginRequest,
    AuthResponse,
    AuthStatusResponse,
    OtpVerifyRequest,
)
from app.modules.runway.services.browser_manager import browser_manager
from app.modules.runway.services.login import LoginService


class AuthService:
    def __init__(self, sessions: SessionRepository, login_service: LoginService) -> None:
        self._sessions = sessions
        self._login_service = login_service

    async def get_status(self) -> AuthStatusResponse:
        last = await self._sessions.last()
        if last is None:
            return AuthStatusResponse(status="disconnected")

        return AuthStatusResponse(
            status=last.status,
            session_id=last.session_id,
            email=last.email,
        )

    async def login(self, payload: AuthLoginRequest) -> AuthResponse:
        session = await self._login_service.login(payload)
        return AuthResponse(
            status=session.status,
            session_id=session.session_id,
            email=session.email,
            message="Mock Runway session created. Replace with Playwright login next.",
        )

    async def verify_otp(self, payload: OtpVerifyRequest) -> AuthResponse:
        # Preserve existing contract: missing session → 200 with status="error",
        # not a 404. The frontend surfaces `message` to the user.
        session = await self._sessions.get(payload.session_id)
        if session is None:
            return AuthResponse(status="error", message="Session not found.")

        session.status = "connected"
        return AuthResponse(
            status="connected",
            session_id=session.session_id,
            email=session.email,
            message="OTP accepted.",
        )

    async def disconnect(self) -> AuthStatusResponse:
        """Clear all stored sessions and rebuild the browser context on next use."""
        await self._sessions.clear_all()
        # Close the scraper's browser so the next login rebuilds from scratch.
        await browser_manager.shutdown()
        return AuthStatusResponse(status="disconnected")
