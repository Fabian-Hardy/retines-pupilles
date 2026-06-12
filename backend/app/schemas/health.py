"""Schemas for health check responses."""

from typing import Literal

from pydantic import BaseModel

HealthStatus = Literal["ok", "error"]


class HealthResponse(BaseModel):
    """Basic health check response."""

    status: HealthStatus
    version: str


class HealthChecks(BaseModel):
    """Dependency check results for readiness."""

    database: HealthStatus


class ReadinessResponse(HealthResponse):
    """Readiness check response."""

    checks: HealthChecks
