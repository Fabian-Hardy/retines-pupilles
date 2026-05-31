"""Central API exception handlers."""

import logging
from collections.abc import Awaitable, Callable, Mapping
from http import HTTPStatus
from typing import Any, cast

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.schemas.error import ApiError, ApiErrorResponse

logger = logging.getLogger("retines")
ExceptionHandler = Callable[[Request, Exception], Response | Awaitable[Response]]

ERROR_CODES_BY_STATUS = {
    status.HTTP_400_BAD_REQUEST: "bad_request",
    status.HTTP_401_UNAUTHORIZED: "unauthorized",
    status.HTTP_403_FORBIDDEN: "forbidden",
    status.HTTP_404_NOT_FOUND: "not_found",
    status.HTTP_409_CONFLICT: "conflict",
    status.HTTP_422_UNPROCESSABLE_CONTENT: "validation_error",
    status.HTTP_500_INTERNAL_SERVER_ERROR: "internal_server_error",
}


def register_exception_handlers(app: FastAPI) -> None:
    """Register API error handlers for the FastAPI app."""

    app.add_exception_handler(
        StarletteHTTPException,
        cast(ExceptionHandler, http_exception_handler),
    )
    app.add_exception_handler(
        RequestValidationError,
        cast(ExceptionHandler, validation_exception_handler),
    )
    app.add_exception_handler(Exception, unhandled_exception_handler)


async def http_exception_handler(
    _request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    """Return the standard error envelope for handled HTTP errors."""

    if exc.status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
        return _error_response(
            status_code=exc.status_code,
            code=_error_code_for_status(exc.status_code),
            message=_default_message_for_status(status.HTTP_500_INTERNAL_SERVER_ERROR),
            details=None,
            headers=exc.headers,
        )

    message, details = _message_and_details_from_http_detail(
        exc.detail,
        status_code=exc.status_code,
    )
    return _error_response(
        status_code=exc.status_code,
        code=_error_code_for_status(exc.status_code),
        message=message,
        details=details,
        headers=exc.headers,
    )


async def validation_exception_handler(
    _request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Return the standard error envelope for request validation errors."""

    return _error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code=ERROR_CODES_BY_STATUS[status.HTTP_422_UNPROCESSABLE_CONTENT],
        message="Request validation failed",
        details=_public_validation_errors(exc),
    )


async def unhandled_exception_handler(
    request: Request,
    _exc: Exception,
) -> JSONResponse:
    """Return a safe generic response for unexpected errors."""

    logger.error("Unhandled API error: %s %s", request.method, request.url.path)
    return _error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code=ERROR_CODES_BY_STATUS[status.HTTP_500_INTERNAL_SERVER_ERROR],
        message="Internal server error",
        details=None,
    )


def _error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | list[Any] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    payload = ApiErrorResponse(
        error=ApiError(code=code, message=message, details=details),
    )
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(mode="json"),
        headers=headers,
    )


def _message_and_details_from_http_detail(
    detail: Any,
    *,
    status_code: int,
) -> tuple[str, dict[str, Any] | list[Any] | None]:
    if detail is None:
        return _default_message_for_status(status_code), None

    if isinstance(detail, str):
        return detail, None

    if isinstance(detail, dict):
        return _default_message_for_status(status_code), detail

    if isinstance(detail, list):
        return _default_message_for_status(status_code), detail

    return _default_message_for_status(status_code), {"detail": detail}


def _public_validation_errors(exc: RequestValidationError) -> list[dict[str, Any]]:
    raw_errors = cast(list[dict[str, Any]], exc.errors())
    return [_public_validation_error(error) for error in raw_errors]


def _public_validation_error(error: dict[str, Any]) -> dict[str, Any]:
    public_error: dict[str, Any] = {}
    for key in ("loc", "msg", "type"):
        if key in error:
            public_error[key] = error[key]
    return public_error


def _error_code_for_status(status_code: int) -> str:
    if status_code in ERROR_CODES_BY_STATUS:
        return ERROR_CODES_BY_STATUS[status_code]

    try:
        http_status = HTTPStatus(status_code)
    except ValueError:
        return "http_error"

    return http_status.phrase.lower().replace(" ", "_").replace("-", "_")


def _default_message_for_status(status_code: int) -> str:
    try:
        return HTTPStatus(status_code).phrase
    except ValueError:
        return "HTTP error"
