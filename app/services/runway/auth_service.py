from app.schemas.runway import (
    AuthLoginRequest,
    AuthResponse,
    AuthStatusResponse,
    OtpVerifyRequest,
)
from app.services.runway.login_service import login_service
from app.services.runway.store import sessions


class RunwayAuthService:
    def get_status(self) -> AuthStatusResponse:
        if not sessions:
            return AuthStatusResponse(status="disconnected")

        last_session = next(reversed(sessions.values()))
        return AuthStatusResponse(
            status=last_session.status,
            session_id=last_session.session_id,
            email=last_session.email,
        )

    def login(self, payload: AuthLoginRequest) -> AuthResponse:
        session = login_service.login(payload)
        return AuthResponse(
            status=session.status,
            session_id=session.session_id,
            email=session.email,
            message="Mock Runway session created. Replace with Playwright login next.",
        )

    def verify_otp(self, payload: OtpVerifyRequest) -> AuthResponse:
        session = sessions.get(payload.session_id)
        if not session:
            return AuthResponse(status="error", message="Session not found.")

        session.status = "connected"
        return AuthResponse(
            status="connected",
            session_id=session.session_id,
            email=session.email,
            message="OTP accepted.",
        )


auth_service = RunwayAuthService()
