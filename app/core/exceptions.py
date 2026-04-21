class AppException(Exception):
    status_code: int = 500
    code: str = "internal_error"

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code


class BadRequest(AppException):
    status_code = 400
    code = "bad_request"


class Unauthorized(AppException):
    status_code = 401
    code = "unauthorized"


class EntityNotFound(AppException):
    status_code = 404
    code = "not_found"


class Conflict(AppException):
    status_code = 409
    code = "conflict"
