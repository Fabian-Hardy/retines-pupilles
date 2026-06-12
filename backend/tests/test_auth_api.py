"""Tests for authentication API endpoints."""

from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.dependencies import auth as auth_dependencies
from app.api.v1.endpoints import auth as auth_endpoints
from app.core.security import create_access_token, decode_access_token
from app.db.session import get_db
from app.main import app
from app.models.user import User
from app.schemas.user import UserCreate


class SessionDouble:
    """Small async-session double for API tests."""

    def __init__(self) -> None:
        self.committed = False

    async def commit(self) -> None:
        self.committed = True


def build_user(
    *,
    user_id: UUID | None = None,
    email: str = "fabian@example.com",
    is_active: bool = True,
) -> User:
    user = User()
    user.id = user_id or uuid4()
    user.created_at = datetime(2026, 5, 30, 9, 0, tzinfo=UTC)
    user.updated_at = datetime(2026, 5, 30, 9, 30, tzinfo=UTC)
    user.email = email
    user.hashed_password = "hashed-password"
    user.full_name = "Fabian Hardy"
    user.is_active = is_active
    user.is_superuser = False
    return user


@pytest.fixture(autouse=True)
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
async def test_register_user_endpoint_returns_created_user(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    override_db_dependency: SessionDouble,
) -> None:
    created_user = build_user()

    async def get_user_by_email_stub(session: object, email: str) -> None:
        assert session is override_db_dependency
        assert email == "fabian@example.com"
        return None

    async def create_user_stub(session: object, user_in: UserCreate) -> User:
        assert session is override_db_dependency
        assert user_in.email == "fabian@example.com"
        assert user_in.password.get_secret_value() == "correct-password"
        return created_user

    monkeypatch.setattr(auth_endpoints, "get_user_by_email", get_user_by_email_stub)
    monkeypatch.setattr(auth_endpoints, "create_user", create_user_stub)

    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "Fabian@example.com",
            "password": "correct-password",
            "full_name": "Fabian Hardy",
        },
    )

    assert response.status_code == 201
    assert override_db_dependency.committed is True

    body = response.json()
    assert body["id"] == str(created_user.id)
    assert body["email"] == "fabian@example.com"
    assert body["full_name"] == "Fabian Hardy"
    assert "hashed_password" not in body


@pytest.mark.asyncio
async def test_register_user_endpoint_rejects_duplicate_email(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    override_db_dependency: SessionDouble,
) -> None:
    existing_user = build_user()

    async def get_user_by_email_stub(session: object, email: str) -> User:
        assert session is override_db_dependency
        assert email == "fabian@example.com"
        return existing_user

    async def create_user_stub(session: object, user_in: UserCreate) -> User:
        pytest.fail("create_user should not be called for duplicate emails")

    monkeypatch.setattr(auth_endpoints, "get_user_by_email", get_user_by_email_stub)
    monkeypatch.setattr(auth_endpoints, "create_user", create_user_stub)

    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "fabian@example.com", "password": "correct-password"},
    )

    assert response.status_code == 409
    assert response.json() == {
        "error": {
            "code": "conflict",
            "message": "Email already registered",
            "details": None,
        },
    }
    assert override_db_dependency.committed is False


@pytest.mark.asyncio
async def test_register_user_endpoint_does_not_echo_invalid_password(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "fabian@example.com", "password": "s3c"},
    )

    assert response.status_code == 422
    assert "s3c" not in response.text
    assert "password" in response.text


@pytest.mark.asyncio
async def test_login_user_endpoint_returns_bearer_token_for_valid_credentials(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    override_db_dependency: SessionDouble,
) -> None:
    user = build_user()

    async def authenticate_user_stub(
        session: object,
        *,
        email: str,
        password: str,
    ) -> User:
        assert session is override_db_dependency
        assert email == "fabian@example.com"
        assert password == "correct-password"
        return user

    monkeypatch.setattr(auth_endpoints, "authenticate_user", authenticate_user_stub)

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "Fabian@example.com", "password": "correct-password"},
    )

    assert response.status_code == 200

    body = response.json()
    assert body["token_type"] == "bearer"
    assert decode_access_token(body["access_token"]) == user.id
    assert "hashed_password" not in body
    assert "hashed_password" not in response.text


@pytest.mark.asyncio
async def test_login_user_endpoint_rejects_invalid_credentials(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def authenticate_user_stub(
        session: object,
        *,
        email: str,
        password: str,
    ) -> None:
        return None

    monkeypatch.setattr(auth_endpoints, "authenticate_user", authenticate_user_stub)

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "fabian@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json() == {
        "error": {
            "code": "unauthorized",
            "message": "Invalid email or password",
            "details": None,
        },
    }


@pytest.mark.asyncio
async def test_logout_user_endpoint_accepts_valid_bearer_token(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    override_db_dependency: SessionDouble,
) -> None:
    user = build_user()
    access_token = create_access_token(user.id)

    async def get_user_stub(session: object, user_id: UUID) -> User:
        assert session is override_db_dependency
        assert user_id == user.id
        return user

    monkeypatch.setattr(auth_dependencies, "get_user", get_user_stub)

    response = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 204
    assert response.content == b""


@pytest.mark.asyncio
async def test_logout_user_endpoint_rejects_missing_token(
    client: AsyncClient,
) -> None:
    response = await client.post("/api/v1/auth/logout")

    assert response.status_code == 401
    assert response.json() == {
        "error": {
            "code": "unauthorized",
            "message": "Not authenticated",
            "details": None,
        },
    }


@pytest.mark.asyncio
async def test_read_current_user_endpoint_returns_user_for_valid_bearer_token(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    override_db_dependency: SessionDouble,
) -> None:
    user = build_user()
    access_token = create_access_token(user.id)

    async def get_user_stub(session: object, user_id: UUID) -> User:
        assert session is override_db_dependency
        assert user_id == user.id
        return user

    monkeypatch.setattr(auth_dependencies, "get_user", get_user_stub)

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200

    body = response.json()
    assert body["id"] == str(user.id)
    assert body["email"] == "fabian@example.com"
    assert "hashed_password" not in body
    assert "hashed_password" not in response.text


@pytest.mark.asyncio
async def test_read_current_user_endpoint_rejects_missing_token(
    client: AsyncClient,
) -> None:
    response = await client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json() == {
        "error": {
            "code": "unauthorized",
            "message": "Not authenticated",
            "details": None,
        },
    }


@pytest.mark.asyncio
async def test_read_current_user_endpoint_rejects_invalid_token(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def get_user_stub(session: object, user_id: UUID) -> User:
        pytest.fail("get_user should not be called for invalid tokens")

    monkeypatch.setattr(auth_dependencies, "get_user", get_user_stub)

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    assert response.json() == {
        "error": {
            "code": "unauthorized",
            "message": "Could not validate credentials",
            "details": None,
        },
    }


@pytest.mark.asyncio
async def test_read_current_user_endpoint_rejects_inactive_user(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    override_db_dependency: SessionDouble,
) -> None:
    user = build_user(is_active=False)
    access_token = create_access_token(user.id)

    async def get_user_stub(session: object, user_id: UUID) -> User:
        assert session is override_db_dependency
        assert user_id == user.id
        return user

    monkeypatch.setattr(auth_dependencies, "get_user", get_user_stub)

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "code": "bad_request",
            "message": "Inactive user",
            "details": None,
        },
    }
