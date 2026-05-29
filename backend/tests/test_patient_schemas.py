"""Tests for Patient Pydantic schemas."""

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.patient import Patient
from app.schemas.patient import PatientCreate, PatientRead, PatientUpdate


def test_patient_create_applies_defaults_and_strips_text_fields() -> None:
    schema = PatientCreate(
        first_name="  Jeanne  ",
        last_name="  Dupont  ",
        date_of_birth=date(1990, 5, 17),
        phone="  +32 470 12 34 56  ",
        city="  Liège  ",
    )

    assert schema.first_name == "Jeanne"
    assert schema.last_name == "Dupont"
    assert schema.date_of_birth == date(1990, 5, 17)
    assert schema.preferred_language == "fr"
    assert schema.phone == "+32 470 12 34 56"
    assert schema.city == "Liège"
    assert schema.country_code == "BE"


def test_patient_create_normalizes_empty_optional_text_fields_to_none() -> None:
    schema = PatientCreate(
        first_name="Jeanne",
        last_name="Dupont",
        date_of_birth=date(1990, 5, 17),
        phone=" ",
        street_line1="",
        city="   ",
    )

    assert schema.phone is None
    assert schema.street_line1 is None
    assert schema.city is None


@pytest.mark.parametrize("field_name", ["first_name", "last_name"])
def test_patient_create_rejects_blank_required_names(field_name: str) -> None:
    payload = {
        "first_name": "Jeanne",
        "last_name": "Dupont",
        "date_of_birth": date(1990, 5, 17),
        field_name: "   ",
    }

    with pytest.raises(ValidationError):
        PatientCreate(**payload)


def test_patient_create_rejects_unsupported_language() -> None:
    with pytest.raises(ValidationError):
        PatientCreate(
            first_name="Jeanne",
            last_name="Dupont",
            date_of_birth=date(1990, 5, 17),
            preferred_language="es",
        )


def test_patient_create_rejects_invalid_country_code_length() -> None:
    with pytest.raises(ValidationError):
        PatientCreate(
            first_name="Jeanne",
            last_name="Dupont",
            date_of_birth=date(1990, 5, 17),
            country_code="BEL",
        )


def test_patient_update_accepts_partial_payload() -> None:
    schema = PatientUpdate(city="  Verviers  ")

    assert schema.city == "Verviers"
    assert schema.model_dump(exclude_unset=True) == {"city": "Verviers"}


def test_patient_update_rejects_blank_required_name_when_provided() -> None:
    with pytest.raises(ValidationError):
        PatientUpdate(first_name="   ")


def test_patient_read_can_be_built_from_patient_orm_model() -> None:
    patient_id = uuid4()
    created_at = datetime(2026, 5, 29, 12, 0, tzinfo=UTC)
    updated_at = datetime(2026, 5, 29, 13, 0, tzinfo=UTC)

    patient = Patient()
    patient.id = patient_id
    patient.created_at = created_at
    patient.updated_at = updated_at
    patient.first_name = "Jeanne"
    patient.last_name = "Dupont"
    patient.date_of_birth = date(1990, 5, 17)
    patient.preferred_language = "fr"
    patient.email = "jeanne.dupont@example.com"
    patient.phone = "+32 470 12 34 56"
    patient.street_line1 = "Rue de la Station 1"
    patient.street_line2 = None
    patient.postal_code = "4800"
    patient.city = "Verviers"
    patient.country_code = "BE"

    schema = PatientRead.model_validate(patient)

    assert schema.id == patient_id
    assert schema.created_at == created_at
    assert schema.updated_at == updated_at
    assert schema.first_name == "Jeanne"
    assert schema.last_name == "Dupont"
    assert schema.date_of_birth == date(1990, 5, 17)
    assert schema.preferred_language == "fr"
    assert schema.email == "jeanne.dupont@example.com"
    assert schema.phone == "+32 470 12 34 56"
    assert schema.street_line1 == "Rue de la Station 1"
    assert schema.street_line2 is None
    assert schema.postal_code == "4800"
    assert schema.city == "Verviers"
    assert schema.country_code == "BE"
