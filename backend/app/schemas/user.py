"""Pydantic schemas for User resources and authentication."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, SecretStr, StringConstraints, field_validator

Password = Annotated[SecretStr, StringConstraints(min_length=8, max_length=128)]
CredentialPassword = Annotated[SecretStr, StringConstraints(min_length=1, max_length=128)]
OptionalFullName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]


def _normalize_email(value: object) -> object:
    if isinstance(value, str):
        return value.strip().lower()
    return value


class UserCreate(BaseModel):
    """Payload used to register a user."""

    email: EmailStr
    password: Password
    full_name: OptionalFullName | None = None

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        """Store and compare email addresses consistently."""

        return _normalize_email(value)


class UserRead(BaseModel):
    """User representation returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    full_name: str | None
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime


class TokenResponse(BaseModel):
    """Bearer access token returned by the login endpoint."""

    access_token: str
    token_type: Literal["bearer"] = "bearer"


class LoginRequest(BaseModel):
    """Payload used to request an access token."""

    email: EmailStr
    password: CredentialPassword

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        """Use the same email normalization as registration."""

        return _normalize_email(value)


__all__ = ["LoginRequest", "TokenResponse", "UserCreate", "UserRead"]
