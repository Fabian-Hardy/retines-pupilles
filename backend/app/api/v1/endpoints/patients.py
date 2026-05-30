"""Patient API endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.patient import (
    PatientListFilters,
    count_patients,
    create_patient,
    delete_patient,
    get_patient,
    list_patients,
    update_patient,
)
from app.db.session import get_db
from app.schemas.patient import (
    LanguageCode,
    PatientCreate,
    PatientListResponse,
    PatientRead,
    PatientUpdate,
)

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


@router.patch("/{patient_id}", response_model=PatientRead)
async def update_patient_endpoint(
    patient_id: UUID,
    patient_in: PatientUpdate,
    session: DbSession,
) -> PatientRead:
    """Partially update a patient."""

    patient = await get_patient(session, patient_id)

    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    updated_patient = await update_patient(session, patient, patient_in)
    await session.commit()

    return PatientRead.model_validate(updated_patient)


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient_endpoint(
    patient_id: UUID,
    session: DbSession,
) -> Response:
    """Delete a patient."""

    patient = await get_patient(session, patient_id)

    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    await delete_patient(session, patient)
    await session.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("", response_model=PatientListResponse)
async def list_patients_endpoint(
    session: DbSession,
    q: Annotated[str | None, Query(max_length=254)] = None,
    first_name: Annotated[str | None, Query(max_length=100)] = None,
    last_name: Annotated[str | None, Query(max_length=100)] = None,
    email: Annotated[str | None, Query(max_length=254)] = None,
    city: Annotated[str | None, Query(max_length=100)] = None,
    postal_code: Annotated[str | None, Query(max_length=16)] = None,
    country_code: Annotated[str | None, Query(min_length=2, max_length=2)] = None,
    preferred_language: Annotated[LanguageCode | None, Query()] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> PatientListResponse:
    """Return a filtered, paginated list of patients."""

    filters = PatientListFilters(
        q=q,
        first_name=first_name,
        last_name=last_name,
        email=email,
        city=city,
        postal_code=postal_code,
        country_code=country_code,
        preferred_language=preferred_language,
    )
    total = await count_patients(session, filters=filters)
    patients = await list_patients(session, filters=filters, offset=offset, limit=limit)

    return PatientListResponse(
        items=[PatientRead.model_validate(patient) for patient in patients],
        total=total,
        offset=offset,
        limit=limit,
    )
