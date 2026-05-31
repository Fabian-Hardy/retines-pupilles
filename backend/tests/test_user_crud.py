"""Tests for User CRUD helpers."""

from typing import cast
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.crud.user import authenticate_user, create_user
from app.models.user import User
from app.schemas.user import UserCreate


class SessionDouble:
    """Small async-session double used to unit-test user CRUD behavior."""

    def __init__(self) -> None:
        self.add: Mock = Mock()
        self.flush: AsyncMock = AsyncMock()
        self.refresh: AsyncMock = AsyncMock()
        self.execute: AsyncMock = AsyncMock()


class SingleResultDouble:
    """SQLAlchemy result double for scalar_one_or_none()."""

    def __init__(self, value: User | None) -> None:
        self._value = value

    def scalar_one_or_none(self) -> User | None:
        return self._value


def build_user(
    *,
    email: str = "fabian@example.com",
    hashed_password: str | None = None,
) -> User:
    user = User()
    user.id = uuid4()
    user.email = email
    user.hashed_password = hashed_password or hash_password("correct-password")
    user.full_name = "Fabian Hardy"
    user.is_active = True
    user.is_superuser = False
    return user


@pytest.mark.asyncio
async def test_create_user_hashes_password_before_persistence() -> None:
    session = SessionDouble()
    payload = UserCreate(
        email="  Fabian@Example.com  ",
        password="correct-password",
        full_name="Fabian Hardy",
    )

    user = await create_user(cast(AsyncSession, session), payload)

    assert user.email == "fabian@example.com"
    assert user.hashed_password != "correct-password"
    assert "correct-password" not in user.hashed_password
    assert verify_password("correct-password", user.hashed_password) is True
    assert user.full_name == "Fabian Hardy"

    session.add.assert_called_once_with(user)
    session.flush.assert_awaited_once()
    session.refresh.assert_awaited_once_with(user)


@pytest.mark.asyncio
async def test_authenticate_user_returns_user_for_valid_password() -> None:
    session = SessionDouble()
    user = build_user()
    session.execute.return_value = SingleResultDouble(user)

    result = await authenticate_user(
        cast(AsyncSession, session),
        email="  Fabian@Example.com  ",
        password="correct-password",
    )

    assert result is user
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_authenticate_user_rejects_wrong_password() -> None:
    session = SessionDouble()
    user = build_user()
    session.execute.return_value = SingleResultDouble(user)

    result = await authenticate_user(
        cast(AsyncSession, session),
        email="fabian@example.com",
        password="wrong-password",
    )

    assert result is None
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_authenticate_user_rejects_malformed_stored_hash() -> None:
    session = SessionDouble()
    user = build_user(hashed_password="not-a-passlib-hash")
    session.execute.return_value = SingleResultDouble(user)

    result = await authenticate_user(
        cast(AsyncSession, session),
        email="fabian@example.com",
        password="correct-password",
    )

    assert result is None
    session.execute.assert_awaited_once()
