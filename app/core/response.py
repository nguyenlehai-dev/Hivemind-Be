from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class SuccessModel(BaseModel):
    """Base for flat success responses with extra top-level fields."""

    success: bool = True


class Envelope(SuccessModel, Generic[T]):
    """Standard envelope: ``{success: true, data: <payload>}``."""

    data: T


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail
