"""Tests for the Patient SQLAlchemy ORM model."""

from uuid import UUID

from sqlalchemy import CheckConstraint, Date, String

from app.db.base import Base
from app.models.patient import Patient


def test_patient_model_uses_expected_table_and_base_metadata() -> None:
    assert Patient.__tablename__ == "patients"
    assert Base.metadata.tables["patients"] is Patient.__table__


def test_patient_model_defines_technical_columns() -> None:
    id_column = Patient.__table__.c.id
    created_at_column = Patient.__table__.c.created_at
    updated_at_column = Patient.__table__.c.updated_at

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
    first_name_column = Patient.__table__.c.first_name
    last_name_column = Patient.__table__.c.last_name
    date_of_birth_column = Patient.__table__.c.date_of_birth

    assert isinstance(first_name_column.type, String)
    assert first_name_column.type.length == 100
    assert first_name_column.nullable is False

    assert isinstance(last_name_column.type, String)
    assert last_name_column.type.length == 100
    assert last_name_column.nullable is False

    assert isinstance(date_of_birth_column.type, Date)
    assert date_of_birth_column.nullable is False


def test_patient_model_defines_contact_and_address_columns() -> None:
    columns = Patient.__table__.c

    assert columns.email.type.length == 254
    assert columns.email.nullable is True

    assert columns.phone.type.length == 32
    assert columns.phone.nullable is True

    assert columns.street_line1.type.length == 255
    assert columns.street_line1.nullable is True

    assert columns.street_line2.type.length == 255
    assert columns.street_line2.nullable is True

    assert columns.postal_code.type.length == 16
    assert columns.postal_code.nullable is True

    assert columns.city.type.length == 100
    assert columns.city.nullable is True

    assert columns.country_code.type.length == 2
    assert columns.country_code.nullable is False
    assert columns.country_code.default is not None
    assert columns.country_code.server_default is not None


def test_patient_model_defines_localization_column() -> None:
    preferred_language_column = Patient.__table__.c.preferred_language

    assert preferred_language_column.type.length == 5
    assert preferred_language_column.nullable is False
    assert preferred_language_column.default is not None
    assert preferred_language_column.server_default is not None


def test_patient_model_defines_minimal_constraints_and_indexes() -> None:
    check_constraint_names = {
        constraint.name
        for constraint in Patient.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }
    index_names = {index.name for index in Patient.__table__.indexes}

    assert "ck_patients_first_name_not_blank" in check_constraint_names
    assert "ck_patients_last_name_not_blank" in check_constraint_names
    assert "ck_patients_preferred_language_supported" in check_constraint_names
    assert "ck_patients_country_code_iso_3166_alpha_2" in check_constraint_names
    assert "ix_patients_identity_lookup" in index_names
