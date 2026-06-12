"""Tests for authentication and authorization dependencies."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid4

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.dependencies import auth as auth_dependencies
from app.api.errors import register_exception_handlers
from app.core.security import create_access_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserRead

CurrentActiveUser = Annotated[User, Depends(auth_dependencies.get_current_active_user)]
CurrentAdminUser = Annotated[User, Depends(auth_dependencies.get_current_admin_user)]


class SessionDouble:
    """Small async-session double for dependency tests."""


def build_user(
    *,
    user_id: UUID | None = None,
    is_active: bool = True,
    is_superuser: bool = False,
) -> User:
    user = User()
    user.id = user_id or uuid4()
    user.created_at = datetime(2026, 5, 30, 9, 0, tzinfo=UTC)
    user.updated_at = datetime(2026, 5, 30, 9, 30, tzinfo=UTC)
    user.email = "fabian@example.com"
    user.hashed_password = "hashed-password"
    user.full_name = "Fabian Hardy"
    user.is_active = is_active
    user.is_superuser = is_superuser
    return user


def build_test_app(session: SessionDouble) -> FastAPI:
    test_app = FastAPI()
    register_exception_handlers(test_app)

    async def get_test_db() -> AsyncIterator[SessionDouble]:
        yield session

    test_app.dependency_overrides[get_db] = get_test_db

    @test_app.get("/me", response_model=UserRead)
    async def read_current_user(current_user: CurrentActiveUser) -> UserRead:
        return UserRead.model_validate(current_user)

    @test_app.get("/admin/me", response_model=UserRead)
    async def read_admin_user(current_user: CurrentAdminUser) -> UserRead:
        return UserRead.model_validate(current_user)

    return test_app


@pytest.fixture
def session() -> SessionDouble:
    return SessionDouble()


@pytest.fixture
async def client(session: SessionDouble) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=build_test_app(session))

    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client


@pytest.mark.asyncio
async def test_current_active_dependency_allows_authenticated_user(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    session: SessionDouble,
) -> None:
    user = build_user(is_superuser=False)
    access_token = create_access_token(user.id)

    async def get_user_stub(session_arg: object, user_id: UUID) -> User:
        assert session_arg is session
        assert user_id == user.id
        return user

    monkeypatch.setattr(auth_dependencies, "get_user", get_user_stub)

    response = await client.get(
        "/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200

    body = response.json()
    assert body["id"] == str(user.id)
    assert body["is_superuser"] is False
    assert "hashed_password" not in body
    assert "hashed_password" not in response.text


@pytest.mark.asyncio
async def test_admin_dependency_allows_admin_user(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    session: SessionDouble,
) -> None:
    user = build_user(is_superuser=True)
    access_token = create_access_token(user.id)

    async def get_user_stub(session_arg: object, user_id: UUID) -> User:
        assert session_arg is session
        assert user_id == user.id
        return user

    monkeypatch.setattr(auth_dependencies, "get_user", get_user_stub)

    response = await client.get(
        "/admin/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200

    body = response.json()
    assert body["id"] == str(user.id)
    assert body["is_superuser"] is True
    assert "hashed_password" not in body
    assert "hashed_password" not in response.text


@pytest.mark.asyncio
async def test_admin_dependency_rejects_non_admin_user(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    session: SessionDouble,
) -> None:
    user = build_user(is_superuser=False)
    access_token = create_access_token(user.id)

    async def get_user_stub(session_arg: object, user_id: UUID) -> User:
        assert session_arg is session
        assert user_id == user.id
        return user

    monkeypatch.setattr(auth_dependencies, "get_user", get_user_stub)

    response = await client.get(
        "/admin/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 403
    assert response.json() == {
        "error": {
            "code": "forbidden",
            "message": "Admin privileges required",
            "details": None,
        },
    }
    assert "hashed_password" not in response.text


@pytest.mark.asyncio
async def test_admin_dependency_rejects_missing_token(
    client: AsyncClient,
) -> None:
    response = await client.get("/admin/me")

    assert response.status_code == 401
    assert response.json() == {
        "error": {
            "code": "unauthorized",
            "message": "Not authenticated",
            "details": None,
        },
    }
    assert "hashed_password" not in response.text
