"""Tests for password and JWT security helpers."""

from datetime import timedelta
from uuid import uuid4

import pytest

from app.core.security import (
    InvalidTokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hashing_verifies_matching_password() -> None:
    hashed_password = hash_password("correct-password")

    assert hashed_password != "correct-password"
    assert verify_password("correct-password", hashed_password) is True
    assert verify_password("wrong-password", hashed_password) is False


def test_access_token_round_trips_user_subject() -> None:
    user_id = uuid4()

    token = create_access_token(user_id)

    assert decode_access_token(token) == user_id


def test_expired_access_token_is_rejected() -> None:
    user_id = uuid4()
    token = create_access_token(user_id, expires_delta=timedelta(seconds=-1))

    with pytest.raises(InvalidTokenError):
        decode_access_token(token)
