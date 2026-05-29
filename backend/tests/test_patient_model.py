"""Tests for the Patient SQLAlchemy ORM model."""

from typing import cast
from uuid import UUID

from sqlalchemy import CheckConstraint, Date, String, Table

from app.db.base import Base
from app.models.patient import Patient


def test_patient_model_uses_expected_table_and_base_metadata() -> None:
    assert Patient.__tablename__ == "patients"
    assert Base.metadata.tables["patients"] is Patient.__table__


def test_patient_model_defines_technical_columns() -> None:
    patient_table = cast(Table, Patient.__table__)

    id_column = patient_table.c.id
    created_at_column = patient_table.c.created_at
    updated_at_column = patient_table.c.updated_at

    assert id_column.primary_key is True
    assert id_column.nullable is False
    assert id_column.default is not None
    assert id_column.type.python_type is UUID

    assert created_at_column.nullable is False
    assert created_at_column.server_default is not None

    assert updated_at_column.nullable is False
    assert updated_at_column.server_default is not None
    assert updated_at_column.onupdate is not None


def test_patient_model_defines_required_identity_columns() -> None:
    patient_table = cast(Table, Patient.__table__)

    first_name_column = patient_table.c.first_name
    last_name_column = patient_table.c.last_name
    date_of_birth_column = patient_table.c.date_of_birth

    first_name_type = cast(String, first_name_column.type)
    last_name_type = cast(String, last_name_column.type)

    assert isinstance(first_name_column.type, String)
    assert first_name_type.length == 100
    assert first_name_column.nullable is False

    assert isinstance(last_name_column.type, String)
    assert last_name_type.length == 100
    assert last_name_column.nullable is False

    assert isinstance(date_of_birth_column.type, Date)
    assert date_of_birth_column.nullable is False


def test_patient_model_defines_contact_and_address_columns() -> None:
    patient_table = cast(Table, Patient.__table__)
    columns = patient_table.c

    email_type = cast(String, columns.email.type)
    phone_type = cast(String, columns.phone.type)
    street_line1_type = cast(String, columns.street_line1.type)
    street_line2_type = cast(String, columns.street_line2.type)
    postal_code_type = cast(String, columns.postal_code.type)
    city_type = cast(String, columns.city.type)
    country_code_type = cast(String, columns.country_code.type)

    assert email_type.length == 254
    assert columns.email.nullable is True

    assert phone_type.length == 32
    assert columns.phone.nullable is True

    assert street_line1_type.length == 255
    assert columns.street_line1.nullable is True

    assert street_line2_type.length == 255
    assert columns.street_line2.nullable is True

    assert postal_code_type.length == 16
    assert columns.postal_code.nullable is True

    assert city_type.length == 100
    assert columns.city.nullable is True

    assert country_code_type.length == 2
    assert columns.country_code.nullable is False
    assert columns.country_code.default is not None
    assert columns.country_code.server_default is not None


def test_patient_model_defines_localization_column() -> None:
    patient_table = cast(Table, Patient.__table__)

    preferred_language_column = patient_table.c.preferred_language
    preferred_language_type = cast(String, preferred_language_column.type)

    assert preferred_language_type.length == 5
    assert preferred_language_column.nullable is False
    assert preferred_language_column.default is not None
    assert preferred_language_column.server_default is not None


def test_patient_model_defines_minimal_constraints_and_indexes() -> None:
    patient_table = cast(Table, Patient.__table__)

    check_constraint_names = {
        constraint.name
        for constraint in patient_table.constraints
        if isinstance(constraint, CheckConstraint) and constraint.name is not None
    }
    index_names = {index.name for index in patient_table.indexes if index.name is not None}

    assert "ck_patients_first_name_not_blank" in check_constraint_names
    assert "ck_patients_last_name_not_blank" in check_constraint_names
    assert "ck_patients_preferred_language_supported" in check_constraint_names
    assert "ck_patients_country_code_iso_3166_alpha_2" in check_constraint_names
    assert "ix_patients_identity_lookup" in index_names
