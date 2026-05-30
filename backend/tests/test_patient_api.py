"""Tests for Patient API endpoints."""

from collections.abc import AsyncIterator, Iterator
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.endpoints import patients as patient_endpoints
from app.crud.patient import PatientListFilters
from app.db.session import get_db
from app.main import app
from app.models.patient import Patient
from app.schemas.patient import PatientCreate, PatientUpdate


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
def override_db_dependency() -> Iterator[SessionDouble]:
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
        session: object,
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

    async def get_patient_stub(session: object, requested_id: UUID) -> Patient | None:
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
    async def get_patient_stub(session: object, requested_id: UUID) -> None:
        return None

    monkeypatch.setattr(patient_endpoints, "get_patient", get_patient_stub)

    response = await client.get(f"/api/v1/patients/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Patient not found"}


@pytest.mark.asyncio
async def test_update_patient_endpoint_updates_patient(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    override_db_dependency: SessionDouble,
) -> None:
    patient_id = uuid4()
    patient = build_patient(patient_id=patient_id)

    async def get_patient_stub(
        session: object,
        requested_id: UUID,
    ) -> Patient | None:
        assert session is override_db_dependency
        assert requested_id == patient_id
        return patient

    async def update_patient_stub(
        session: object,
        patient_to_update: Patient,
        patient_in: PatientUpdate,
    ) -> Patient:
        assert session is override_db_dependency
        assert patient_to_update is patient
        assert patient_in.city == "Liege"

        patient.city = patient_in.city
        return patient

    monkeypatch.setattr(patient_endpoints, "get_patient", get_patient_stub)
    monkeypatch.setattr(patient_endpoints, "update_patient", update_patient_stub)

    response = await client.patch(
        f"/api/v1/patients/{patient_id}",
        json={"city": "Liege"},
    )

    assert response.status_code == 200
    assert override_db_dependency.committed is True

    body = response.json()
    assert body["id"] == str(patient_id)
    assert body["city"] == "Liege"


@pytest.mark.asyncio
async def test_update_patient_endpoint_returns_404_when_missing(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    override_db_dependency: SessionDouble,
) -> None:
    async def get_patient_stub(
        session: object,
        requested_id: UUID,
    ) -> None:
        return None

    async def update_patient_stub(
        session: object,
        patient_to_update: Patient,
        patient_in: PatientUpdate,
    ) -> Patient:
        pytest.fail("update_patient should not be called when patient is missing")

    monkeypatch.setattr(patient_endpoints, "get_patient", get_patient_stub)
    monkeypatch.setattr(patient_endpoints, "update_patient", update_patient_stub)

    response = await client.patch(
        f"/api/v1/patients/{uuid4()}",
        json={"city": "Liege"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Patient not found"}
    assert override_db_dependency.committed is False


@pytest.mark.asyncio
async def test_delete_patient_endpoint_deletes_patient(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    override_db_dependency: SessionDouble,
) -> None:
    patient_id = uuid4()
    patient = build_patient(patient_id=patient_id)
    deleted = False

    async def get_patient_stub(
        session: object,
        requested_id: UUID,
    ) -> Patient | None:
        assert session is override_db_dependency
        assert requested_id == patient_id
        return patient

    async def delete_patient_stub(
        session: object,
        patient_to_delete: Patient,
    ) -> None:
        nonlocal deleted

        assert session is override_db_dependency
        assert patient_to_delete is patient
        deleted = True

    monkeypatch.setattr(patient_endpoints, "get_patient", get_patient_stub)
    monkeypatch.setattr(patient_endpoints, "delete_patient", delete_patient_stub)

    response = await client.delete(f"/api/v1/patients/{patient_id}")

    assert response.status_code == 204
    assert response.content == b""
    assert deleted is True
    assert override_db_dependency.committed is True


@pytest.mark.asyncio
async def test_delete_patient_endpoint_returns_404_when_missing(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    override_db_dependency: SessionDouble,
) -> None:
    async def get_patient_stub(
        session: object,
        requested_id: UUID,
    ) -> None:
        return None

    async def delete_patient_stub(
        session: object,
        patient_to_delete: Patient,
    ) -> None:
        pytest.fail("delete_patient should not be called when patient is missing")

    monkeypatch.setattr(patient_endpoints, "get_patient", get_patient_stub)
    monkeypatch.setattr(patient_endpoints, "delete_patient", delete_patient_stub)

    response = await client.delete(f"/api/v1/patients/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Patient not found"}
    assert override_db_dependency.committed is False


@pytest.mark.asyncio
async def test_list_patients_endpoint_returns_paginated_response_shape(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_patient = build_patient(first_name="Jeanne", last_name="Dupont")
    second_patient = build_patient(first_name="Louis", last_name="Martin")

    async def count_patients_stub(
        session: object,
        *,
        filters: PatientListFilters | None = None,
    ) -> int:
        assert filters == PatientListFilters()
        return 2

    async def list_patients_stub(
        session: object,
        *,
        filters: PatientListFilters | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Patient]:
        assert filters == PatientListFilters()
        assert offset == 0
        assert limit == 100
        return [first_patient, second_patient]

    monkeypatch.setattr(patient_endpoints, "count_patients", count_patients_stub)
    monkeypatch.setattr(patient_endpoints, "list_patients", list_patients_stub)

    response = await client.get("/api/v1/patients")

    assert response.status_code == 200

    body: dict[str, Any] = response.json()
    assert set(body) == {"items", "total", "offset", "limit"}
    assert body["total"] == 2
    assert body["offset"] == 0
    assert body["limit"] == 100
    assert len(body["items"]) == 2
    assert body["items"][0]["first_name"] == "Jeanne"
    assert body["items"][1]["first_name"] == "Louis"


@pytest.mark.asyncio
async def test_list_patients_endpoint_forwards_pagination(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def count_patients_stub(
        session: object,
        *,
        filters: PatientListFilters | None = None,
    ) -> int:
        assert filters == PatientListFilters()
        return 0

    async def list_patients_stub(
        session: object,
        *,
        filters: PatientListFilters | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Patient]:
        assert filters == PatientListFilters()
        assert offset == 5
        assert limit == 10
        return []

    monkeypatch.setattr(patient_endpoints, "count_patients", count_patients_stub)
    monkeypatch.setattr(patient_endpoints, "list_patients", list_patients_stub)

    response = await client.get("/api/v1/patients?offset=5&limit=10")

    assert response.status_code == 200
    assert response.json()["offset"] == 5
    assert response.json()["limit"] == 10


@pytest.mark.parametrize(
    ("query_string", "expected_filters"),
    [
        ("last_name=Dupont", PatientListFilters(last_name="Dupont")),
        ("city=Verviers", PatientListFilters(city="Verviers")),
        ("preferred_language=nl", PatientListFilters(preferred_language="nl")),
        ("q=jeanne", PatientListFilters(q="jeanne")),
    ],
    ids=["last_name", "city", "preferred_language", "q"],
)
@pytest.mark.asyncio
async def test_list_patients_endpoint_forwards_filters(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    query_string: str,
    expected_filters: PatientListFilters,
) -> None:
    async def count_patients_stub(
        session: object,
        *,
        filters: PatientListFilters | None = None,
    ) -> int:
        assert filters == expected_filters
        return 0

    async def list_patients_stub(
        session: object,
        *,
        filters: PatientListFilters | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Patient]:
        assert filters == expected_filters
        assert offset == 0
        assert limit == 100
        return []

    monkeypatch.setattr(patient_endpoints, "count_patients", count_patients_stub)
    monkeypatch.setattr(patient_endpoints, "list_patients", list_patients_stub)

    response = await client.get(f"/api/v1/patients?{query_string}")

    assert response.status_code == 200


@pytest.mark.parametrize(
    "query_string",
    ["offset=-1", "limit=0", "limit=101"],
    ids=["negative_offset", "zero_limit", "limit_above_maximum"],
)
@pytest.mark.asyncio
async def test_list_patients_endpoint_rejects_invalid_pagination(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    query_string: str,
) -> None:
    async def count_patients_stub(
        session: object,
        *,
        filters: PatientListFilters | None = None,
    ) -> int:
        pytest.fail("count_patients should not be called for invalid pagination")

    async def list_patients_stub(
        session: object,
        *,
        filters: PatientListFilters | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Patient]:
        pytest.fail("list_patients should not be called for invalid pagination")

    monkeypatch.setattr(patient_endpoints, "count_patients", count_patients_stub)
    monkeypatch.setattr(patient_endpoints, "list_patients", list_patients_stub)

    response = await client.get(f"/api/v1/patients?{query_string}")

    assert response.status_code == 422
