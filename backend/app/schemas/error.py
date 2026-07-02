"""Schemas for standard API error responses."""

from typing import Any

from pydantic import BaseModel


class ApiError(BaseModel):
    """Standard API error body."""

    code: str
    message: str
    details: dict[str, Any] | list[Any] | None = None


class ApiErrorResponse(BaseModel):
    """Standard API error response envelope."""

    error: ApiError
