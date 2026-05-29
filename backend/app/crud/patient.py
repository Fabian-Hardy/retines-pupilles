"""CRUD helpers for Patient resources."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
    offset: int = 0,
    limit: int = 100,
) -> Sequence[Patient]:
    """Return patients ordered by identity fields."""

    result = await session.execute(
        select(Patient)
        .order_by(Patient.last_name, Patient.first_name, Patient.date_of_birth)
        .offset(offset)
        .limit(limit)
    )

    return result.scalars().all()


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
    "create_patient",
    "delete_patient",
    "get_patient",
    "list_patients",
    "update_patient",
]
