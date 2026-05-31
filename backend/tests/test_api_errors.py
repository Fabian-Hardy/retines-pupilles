"""Tests for the standard API error contract."""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.errors import register_exception_handlers


@pytest.mark.asyncio
async def test_unhandled_exception_returns_safe_standard_error() -> None:
    test_app = FastAPI()
    register_exception_handlers(test_app)

    @test_app.get("/explode")
    async def explode() -> None:
        raise RuntimeError("database password=s3cr3t")

    transport = ASGITransport(app=test_app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/explode")

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "internal_server_error",
            "message": "Internal server error",
            "details": None,
        },
    }
    assert "s3cr3t" not in response.text
    assert "database password" not in response.text
