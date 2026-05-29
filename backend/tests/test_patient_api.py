"""Tests for Patient API endpoints."""

from collections.abc import AsyncIterator
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints import patients as patient_endpoints
from app.db.session import get_db
from app.main import app
from app.models.patient import Patient
from app.schemas.patient import PatientCreate


class SessionDouble:
    """Small async-session double for API tests."""

    def __init__(self) -> None:
        self.committed = False

    async def commit(self) -> None:
        self.committed = True


def build_patient(
    *,
    patient_id: UUID | None = None,
    first_name: str = "Jeanne",
    last_name: str = "Dupont",
    city: str | None = "Verviers",
) -> Patient:
    patient = Patient()
    patient.id = patient_id or uuid4()
    patient.created_at = datetime(2026, 5, 29, 12, 0, tzinfo=UTC)
    patient.updated_at = datetime(2026, 5, 29, 13, 0, tzinfo=UTC)
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


@pytest.fixture(autouse=True)
def override_db_dependency() -> AsyncIterator[SessionDouble]:
    session = SessionDouble()

    async def get_test_db() -> AsyncIterator[SessionDouble]:
        yield session

    app.dependency_overrides[get_db] = get_test_db

    yield session

    app.dependency_overrides.clear()


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client


@pytest.mark.asyncio
async def test_create_patient_endpoint_returns_created_patient(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    override_db_dependency: SessionDouble,
) -> None:
    created_patient = build_patient()

    async def create_patient_stub(
        session: AsyncSession,
        patient_in: PatientCreate,
    ) -> Patient:
        assert patient_in.first_name == "Jeanne"
        assert patient_in.last_name == "Dupont"
        assert session is override_db_dependency
        return created_patient

    monkeypatch.setattr(patient_endpoints, "create_patient", create_patient_stub)

    response = await client.post(
        "/api/v1/patients",
        json={
            "first_name": "Jeanne",
            "last_name": "Dupont",
            "date_of_birth": "1990-05-17",
            "email": "jeanne.dupont@example.com",
            "city": "Verviers",
        },
    )

    assert response.status_code == 201
    assert override_db_dependency.committed is True

    body = response.json()
    assert body["id"] == str(created_patient.id)
    assert body["first_name"] == "Jeanne"
    assert body["last_name"] == "Dupont"
    assert body["email"] == "jeanne.dupont@example.com"


@pytest.mark.asyncio
async def test_get_patient_endpoint_returns_patient(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patient_id = uuid4()
    patient = build_patient(patient_id=patient_id)

    async def get_patient_stub(session: AsyncSession, requested_id: UUID) -> Patient | None:
        assert requested_id == patient_id
        return patient

    monkeypatch.setattr(patient_endpoints, "get_patient", get_patient_stub)

    response = await client.get(f"/api/v1/patients/{patient_id}")

    assert response.status_code == 200

    body = response.json()
    assert body["id"] == str(patient_id)
    assert body["first_name"] == "Jeanne"


@pytest.mark.asyncio
async def test_get_patient_endpoint_returns_404_when_missing(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def get_patient_stub(session: AsyncSession, requested_id: UUID) -> None:
        return None

    monkeypatch.setattr(patient_endpoints, "get_patient", get_patient_stub)

    response = await client.get(f"/api/v1/patients/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Patient not found"}


@pytest.mark.asyncio
async def test_list_patients_endpoint_returns_patients(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_patient = build_patient(first_name="Jeanne", last_name="Dupont")
    second_patient = build_patient(first_name="Louis", last_name="Martin")

    async def list_patients_stub(
        session: AsyncSession,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Patient]:
        assert offset == 5
        assert limit == 10
        return [first_patient, second_patient]

    monkeypatch.setattr(patient_endpoints, "list_patients", list_patients_stub)

    response = await client.get("/api/v1/patients?offset=5&limit=10")

    assert response.status_code == 200

    body: list[dict[str, Any]] = response.json()
    assert len(body) == 2
    assert body[0]["first_name"] == "Jeanne"
    assert body[1]["first_name"] == "Louis"


@pytest.mark.asyncio
async def test_list_patients_endpoint_rejects_invalid_limit(client: AsyncClient) -> None:
    response = await client.get("/api/v1/patients?limit=0")

    assert response.status_code == 422
