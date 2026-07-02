"""Tests for Patient CRUD helpers."""

from datetime import date
from typing import cast
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.patient import (
    create_patient,
    delete_patient,
    get_patient,
    list_patients,
    update_patient,
)
from app.models.patient import Patient
from app.schemas.patient import PatientCreate, PatientUpdate


class SessionDouble:
    """Small async-session double used to unit-test CRUD behavior."""

    def __init__(self) -> None:
        self.add: Mock = Mock()
        self.flush: AsyncMock = AsyncMock()
        self.refresh: AsyncMock = AsyncMock()
        self.execute: AsyncMock = AsyncMock()
        self.delete: AsyncMock = AsyncMock()


class SingleResultDouble:
    """SQLAlchemy result double for scalar_one_or_none()."""

    def __init__(self, value: Patient | None) -> None:
        self._value = value

    def scalar_one_or_none(self) -> Patient | None:
        return self._value


class ScalarCollectionDouble:
    """SQLAlchemy scalar collection double for all()."""

    def __init__(self, values: list[Patient]) -> None:
        self._values = values

    def all(self) -> list[Patient]:
        return self._values


class ListResultDouble:
    """SQLAlchemy result double for scalars().all()."""

    def __init__(self, values: list[Patient]) -> None:
        self._values = values

    def scalars(self) -> ScalarCollectionDouble:
        return ScalarCollectionDouble(self._values)


def build_patient(
    *,
    first_name: str = "Jeanne",
    last_name: str = "Dupont",
    city: str | None = "Verviers",
) -> Patient:
    patient = Patient()
    patient.id = uuid4()
    patient.first_name = first_name
    patient.last_name = last_name
    patient.date_of_birth = date(1990, 5, 17)
    patient.preferred_language = "fr"
    patient.email = "jeanne.dupont@example.com"
    patient.phone = "+32 470 12 34 56"
    patient.street_line1 = "Rue de la Station 1"
    patient.street_line2 = None
    patient.postal_code = "4800"
    patient.city = city
    patient.country_code = "BE"
    return patient


@pytest.mark.asyncio
async def test_create_patient_builds_model_and_flushes_session() -> None:
    session = SessionDouble()
    payload = PatientCreate(
        first_name="Jeanne",
        last_name="Dupont",
        date_of_birth=date(1990, 5, 17),
        email="jeanne.dupont@example.com",
        city="Verviers",
    )

    patient = await create_patient(cast(AsyncSession, session), payload)

    assert patient.first_name == "Jeanne"
    assert patient.last_name == "Dupont"
    assert patient.date_of_birth == date(1990, 5, 17)
    assert patient.email == "jeanne.dupont@example.com"
    assert patient.city == "Verviers"
    assert patient.preferred_language == "fr"
    assert patient.country_code == "BE"

    session.add.assert_called_once_with(patient)
    session.flush.assert_awaited_once()
    session.refresh.assert_awaited_once_with(patient)


@pytest.mark.asyncio
async def test_get_patient_returns_matching_patient() -> None:
    session = SessionDouble()
    patient = build_patient()
    session.execute.return_value = SingleResultDouble(patient)

    result = await get_patient(cast(AsyncSession, session), patient.id)

    assert result is patient
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_patient_returns_none_when_missing() -> None:
    session = SessionDouble()
    session.execute.return_value = SingleResultDouble(None)

    result = await get_patient(cast(AsyncSession, session), uuid4())

    assert result is None
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_patients_returns_ordered_result_values() -> None:
    session = SessionDouble()
    first_patient = build_patient(first_name="Jeanne", last_name="Dupont")
    second_patient = build_patient(first_name="Louis", last_name="Martin")
    session.execute.return_value = ListResultDouble([first_patient, second_patient])

    result = await list_patients(cast(AsyncSession, session), offset=5, limit=10)

    assert result == [first_patient, second_patient]
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_patient_applies_partial_payload_and_flushes_session() -> None:
    session = SessionDouble()
    patient = build_patient(city="Verviers")
    payload = PatientUpdate(city="Liège", email=None)

    result = await update_patient(cast(AsyncSession, session), patient, payload)

    assert result is patient
    assert patient.city == "Liège"
    assert patient.email is None
    assert patient.first_name == "Jeanne"
    assert patient.last_name == "Dupont"

    session.flush.assert_awaited_once()
    session.refresh.assert_awaited_once_with(patient)


@pytest.mark.asyncio
async def test_delete_patient_deletes_model_and_flushes_session() -> None:
    session = SessionDouble()
    patient = build_patient()

    await delete_patient(cast(AsyncSession, session), patient)

    session.delete.assert_awaited_once_with(patient)
    session.flush.assert_awaited_once()
    session.refresh.assert_not_awaited()
