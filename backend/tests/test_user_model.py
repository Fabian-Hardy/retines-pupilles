"""Tests for the User SQLAlchemy ORM model."""

from typing import cast
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, String, Table

from app.db.base import Base
from app.models.user import User


def test_user_model_uses_expected_table_and_base_metadata() -> None:
    assert User.__tablename__ == "users"
    assert Base.metadata.tables["users"] is User.__table__


def test_user_model_defines_technical_columns() -> None:
    user_table = cast(Table, User.__table__)

    id_column = user_table.c.id
    created_at_column = user_table.c.created_at
    updated_at_column = user_table.c.updated_at

    assert id_column.primary_key is True
    assert id_column.nullable is False
    assert id_column.default is not None
    assert id_column.type.python_type is UUID

    assert created_at_column.nullable is False
    assert created_at_column.server_default is not None

    assert updated_at_column.nullable is False
    assert updated_at_column.server_default is not None
    assert updated_at_column.onupdate is not None


def test_user_model_defines_authentication_columns() -> None:
    user_table = cast(Table, User.__table__)
    columns = user_table.c

    email_type = cast(String, columns.email.type)
    hashed_password_type = cast(String, columns.hashed_password.type)
    full_name_type = cast(String, columns.full_name.type)

    assert email_type.length == 254
    assert columns.email.nullable is False
    assert columns.email.unique is True

    assert hashed_password_type.length == 255
    assert columns.hashed_password.nullable is False

    assert full_name_type.length == 255
    assert columns.full_name.nullable is True

    assert isinstance(columns.is_active.type, Boolean)
    assert columns.is_active.nullable is False
    assert columns.is_active.default is not None
    assert columns.is_active.server_default is not None

    assert isinstance(columns.is_superuser.type, Boolean)
    assert columns.is_superuser.nullable is False
    assert columns.is_superuser.default is not None
    assert columns.is_superuser.server_default is not None


def test_user_model_defines_email_constraint_and_unique_index() -> None:
    user_table = cast(Table, User.__table__)

    check_constraint_names = {
        constraint.name
        for constraint in user_table.constraints
        if isinstance(constraint, CheckConstraint) and constraint.name is not None
    }
    email_indexes = [
        index
        for index in user_table.indexes
        if index.name == "ix_users_email"
    ]

    assert "ck_users_email_not_blank" in check_constraint_names
    assert len(email_indexes) == 1
    assert email_indexes[0].unique is True
