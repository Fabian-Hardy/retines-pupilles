"""Tests for User Pydantic schemas."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.user import User
from app.schemas.user import LoginRequest, TokenResponse, UserCreate, UserRead


def test_user_create_normalizes_email_and_strips_full_name() -> None:
    schema = UserCreate(
        email="  Fabian@Example.com  ",
        password="correct-password",
        full_name="  Fabian Hardy  ",
    )

    assert schema.email == "fabian@example.com"
    assert schema.password == "correct-password"
    assert schema.full_name == "Fabian Hardy"


def test_user_create_rejects_short_password() -> None:
    with pytest.raises(ValidationError):
        UserCreate(email="fabian@example.com", password="short")


def test_login_request_normalizes_email() -> None:
    schema = LoginRequest(email="  Fabian@Example.com  ", password="secret")

    assert schema.email == "fabian@example.com"
    assert schema.password == "secret"


def test_token_response_defaults_to_bearer_token_type() -> None:
    schema = TokenResponse(access_token="access-token")

    assert schema.access_token == "access-token"
    assert schema.token_type == "bearer"


def test_user_read_can_be_built_from_user_orm_model() -> None:
    user_id = uuid4()
    created_at = datetime(2026, 5, 30, 9, 0, tzinfo=UTC)
    updated_at = datetime(2026, 5, 30, 9, 30, tzinfo=UTC)

    user = User()
    user.id = user_id
    user.created_at = created_at
    user.updated_at = updated_at
    user.email = "fabian@example.com"
    user.hashed_password = "hashed-password"
    user.full_name = "Fabian Hardy"
    user.is_active = True
    user.is_superuser = False

    schema = UserRead.model_validate(user)

    assert schema.id == user_id
    assert schema.created_at == created_at
    assert schema.updated_at == updated_at
    assert schema.email == "fabian@example.com"
    assert schema.full_name == "Fabian Hardy"
    assert schema.is_active is True
    assert schema.is_superuser is False
