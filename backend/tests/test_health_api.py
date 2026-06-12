"""Tests for health check API endpoints."""

from collections.abc import AsyncIterator, Iterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.db.session import get_db
from app.main import app


class SessionDouble:
    """Small async-session double for readiness tests."""

    def __init__(self) -> None:
        self.should_fail = False
        self.statements: list[str] = []

    async def execute(self, statement: object) -> None:
        self.statements.append(str(statement))
        if self.should_fail:
            raise RuntimeError("database password=s3cr3t")


@pytest.fixture
def override_db_dependency() -> Iterator[SessionDouble]:
    session = SessionDouble()

    async def get_test_db() -> AsyncIterator[SessionDouble]:
        yield session

    app.dependency_overrides[get_db] = get_test_db

    yield session

    app.dependency_overrides.clear()


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client


@pytest.mark.asyncio
async def test_health_endpoint_returns_safe_application_status(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "version": settings.APP_VERSION,
    }


@pytest.mark.asyncio
async def test_liveness_endpoint_does_not_check_database(
    client: AsyncClient,
    override_db_dependency: SessionDouble,
) -> None:
    override_db_dependency.should_fail = True

    response = await client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "version": settings.APP_VERSION,
    }
    assert override_db_dependency.statements == []


@pytest.mark.asyncio
async def test_readiness_endpoint_checks_database(
    client: AsyncClient,
    override_db_dependency: SessionDouble,
) -> None:
    response = await client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "version": settings.APP_VERSION,
        "checks": {"database": "ok"},
    }
    assert override_db_dependency.statements == ["SELECT 1"]


@pytest.mark.asyncio
async def test_readiness_endpoint_returns_safe_503_when_database_check_fails(
    client: AsyncClient,
    override_db_dependency: SessionDouble,
) -> None:
    override_db_dependency.should_fail = True

    response = await client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "error",
        "version": settings.APP_VERSION,
        "checks": {"database": "error"},
    }
    assert "s3cr3t" not in response.text
    assert "database password" not in response.text
    assert "RuntimeError" not in response.text
