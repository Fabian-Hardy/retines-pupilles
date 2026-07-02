"""CRUD helpers for Patient resources."""

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.models.patient import Patient
from app.schemas.patient import PatientCreate, PatientUpdate

_PATIENT_MUTABLE_FIELDS = (
    "first_name",
    "last_name",
    "date_of_birth",
    "preferred_language",
    "email",
    "phone",
    "street_line1",
    "street_line2",
    "postal_code",
    "city",
    "country_code",
)


@dataclass(frozen=True, kw_only=True)
class PatientListFilters:
    """Optional filters for patient list queries."""

    q: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    city: str | None = None
    postal_code: str | None = None
    country_code: str | None = None
    preferred_language: str | None = None


def _normalize_filter(value: str | None) -> str | None:
    if value is None:
        return None

    stripped = value.strip()
    return stripped or None


def _like_pattern(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _patient_filter_conditions(filters: PatientListFilters) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = []

    q = _normalize_filter(filters.q)
    if q is not None:
        pattern = _like_pattern(q)
        conditions.append(
            or_(
                Patient.first_name.ilike(pattern, escape="\\"),
                Patient.last_name.ilike(pattern, escape="\\"),
                Patient.email.ilike(pattern, escape="\\"),
                Patient.phone.ilike(pattern, escape="\\"),
            )
        )

    first_name = _normalize_filter(filters.first_name)
    if first_name is not None:
        conditions.append(Patient.first_name == first_name)

    last_name = _normalize_filter(filters.last_name)
    if last_name is not None:
        conditions.append(Patient.last_name == last_name)

    email = _normalize_filter(filters.email)
    if email is not None:
        conditions.append(Patient.email == email)

    city = _normalize_filter(filters.city)
    if city is not None:
        conditions.append(Patient.city == city)

    postal_code = _normalize_filter(filters.postal_code)
    if postal_code is not None:
        conditions.append(Patient.postal_code == postal_code)

    country_code = _normalize_filter(filters.country_code)
    if country_code is not None:
        conditions.append(Patient.country_code == country_code.upper())

    preferred_language = _normalize_filter(filters.preferred_language)
    if preferred_language is not None:
        conditions.append(Patient.preferred_language == preferred_language)

    return conditions


async def create_patient(session: AsyncSession, patient_in: PatientCreate) -> Patient:
    """Create a patient record without committing the transaction."""

    patient = Patient()

    for field_name in _PATIENT_MUTABLE_FIELDS:
        setattr(patient, field_name, getattr(patient_in, field_name))

    session.add(patient)
    await session.flush()
    await session.refresh(patient)

    return patient


async def get_patient(session: AsyncSession, patient_id: UUID) -> Patient | None:
    """Return a patient by ID, or None when no matching row exists."""

    result = await session.execute(select(Patient).where(Patient.id == patient_id))
    return result.scalar_one_or_none()


async def list_patients(
    session: AsyncSession,
    *,
    filters: PatientListFilters | None = None,
    offset: int = 0,
    limit: int = 100,
) -> Sequence[Patient]:
    """Return patients ordered by identity fields."""

    conditions = _patient_filter_conditions(filters or PatientListFilters())

    result = await session.execute(
        select(Patient)
        .where(*conditions)
        .order_by(Patient.last_name, Patient.first_name, Patient.date_of_birth, Patient.id)
        .offset(offset)
        .limit(limit)
    )

    return result.scalars().all()


async def count_patients(
    session: AsyncSession,
    *,
    filters: PatientListFilters | None = None,
) -> int:
    """Return the number of patients matching the provided filters."""

    conditions = _patient_filter_conditions(filters or PatientListFilters())

    result = await session.execute(select(func.count()).select_from(Patient).where(*conditions))

    return int(result.scalar_one())


async def update_patient(
    session: AsyncSession,
    patient: Patient,
    patient_in: PatientUpdate,
) -> Patient:
    """Apply a partial update to a patient without committing the transaction."""

    update_data = patient_in.model_dump(exclude_unset=True)

    for field_name, value in update_data.items():
        setattr(patient, field_name, value)

    await session.flush()
    await session.refresh(patient)

    return patient


async def delete_patient(session: AsyncSession, patient: Patient) -> None:
    """Delete a patient without committing the transaction."""

    await session.delete(patient)
    await session.flush()


__all__ = [
    "PatientListFilters",
    "count_patients",
    "create_patient",
    "delete_patient",
    "get_patient",
    "list_patients",
    "update_patient",
]
