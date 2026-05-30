"""Pydantic schemas for Patient resources."""

from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, StringConstraints, field_validator

LanguageCode = Literal["fr", "nl", "de", "en"]

RequiredName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]
OptionalPhone = Annotated[
    str,
    StringConstraints(strip_whitespace=True, max_length=32),
]
OptionalAddressLine = Annotated[
    str,
    StringConstraints(strip_whitespace=True, max_length=255),
]
OptionalPostalCode = Annotated[
    str,
    StringConstraints(strip_whitespace=True, max_length=16),
]
OptionalCity = Annotated[
    str,
    StringConstraints(strip_whitespace=True, max_length=100),
]
CountryCode = Annotated[
    str,
    StringConstraints(strip_whitespace=True, to_upper=True, min_length=2, max_length=2),
]


class PatientCreate(BaseModel):
    """Payload used to create a patient."""

    first_name: RequiredName
    last_name: RequiredName
    date_of_birth: date
    preferred_language: LanguageCode = "fr"

    email: EmailStr | None = None
    phone: OptionalPhone | None = None
    street_line1: OptionalAddressLine | None = None
    street_line2: OptionalAddressLine | None = None
    postal_code: OptionalPostalCode | None = None
    city: OptionalCity | None = None
    country_code: CountryCode = "BE"

    @field_validator(
        "email",
        "phone",
        "street_line1",
        "street_line2",
        "postal_code",
        "city",
        mode="before",
    )
    @classmethod
    def empty_string_to_none(cls, value: object) -> object:
        """Normalize empty optional text fields to None."""

        if isinstance(value, str) and value.strip() == "":
            return None
        return value


class PatientUpdate(BaseModel):
    """Payload used to partially update a patient."""

    first_name: RequiredName | None = None
    last_name: RequiredName | None = None
    date_of_birth: date | None = None
    preferred_language: LanguageCode | None = None

    email: EmailStr | None = None
    phone: OptionalPhone | None = None
    street_line1: OptionalAddressLine | None = None
    street_line2: OptionalAddressLine | None = None
    postal_code: OptionalPostalCode | None = None
    city: OptionalCity | None = None
    country_code: CountryCode | None = None

    @field_validator(
        "email",
        "phone",
        "street_line1",
        "street_line2",
        "postal_code",
        "city",
        mode="before",
    )
    @classmethod
    def empty_string_to_none(cls, value: object) -> object:
        """Normalize empty optional text fields to None."""

        if isinstance(value, str) and value.strip() == "":
            return None
        return value


class PatientRead(BaseModel):
    """Patient representation returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime

    first_name: str
    last_name: str
    date_of_birth: date
    preferred_language: LanguageCode

    email: EmailStr | None
    phone: str | None
    street_line1: str | None
    street_line2: str | None
    postal_code: str | None
    city: str | None
    country_code: str


class PatientListResponse(BaseModel):
    """Paginated patient list response."""

    items: list[PatientRead]
    total: int
    offset: int
    limit: int


__all__ = ["PatientCreate", "PatientListResponse", "PatientRead", "PatientUpdate"]
