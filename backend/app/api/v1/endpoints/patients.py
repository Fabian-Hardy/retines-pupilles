"""Patient API endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.patient import create_patient, get_patient, list_patients
from app.db.session import get_db
from app.schemas.patient import PatientCreate, PatientRead

router = APIRouter(prefix="/patients", tags=["patients"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post("", response_model=PatientRead, status_code=status.HTTP_201_CREATED)
async def create_patient_endpoint(
    patient_in: PatientCreate,
    session: DbSession,
) -> PatientRead:
    """Create a patient."""

    patient = await create_patient(session, patient_in)
    await session.commit()

    return PatientRead.model_validate(patient)


@router.get("/{patient_id}", response_model=PatientRead)
async def get_patient_endpoint(
    patient_id: UUID,
    session: DbSession,
) -> PatientRead:
    """Return a patient by ID."""

    patient = await get_patient(session, patient_id)

    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    return PatientRead.model_validate(patient)


@router.get("", response_model=list[PatientRead])
async def list_patients_endpoint(
    session: DbSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[PatientRead]:
    """Return a paginated list of patients."""

    patients = await list_patients(session, offset=offset, limit=limit)

    return [PatientRead.model_validate(patient) for patient in patients]
