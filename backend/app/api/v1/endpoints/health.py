from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.schemas.health import HealthChecks, HealthResponse, ReadinessResponse

router = APIRouter(prefix="/health", tags=["health"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=HealthResponse)
async def health() -> HealthResponse:
    return _healthy_response()


@router.get("/live", response_model=HealthResponse)
async def liveness() -> HealthResponse:
    return _healthy_response()


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ReadinessResponse}},
)
async def readiness(session: DbSession, response: Response) -> ReadinessResponse:
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadinessResponse(
            status="error",
            version=settings.APP_VERSION,
            checks=HealthChecks(database="error"),
        )

    return ReadinessResponse(
        status="ok",
        version=settings.APP_VERSION,
        checks=HealthChecks(database="ok"),
    )


def _healthy_response() -> HealthResponse:
    return HealthResponse(status="ok", version=settings.APP_VERSION)
