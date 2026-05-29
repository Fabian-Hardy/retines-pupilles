"""Tests for shared SQLAlchemy ORM mixins."""

from uuid import UUID

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class TechnicalModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Test-only mapped model using common technical mixins."""

    __tablename__ = "technical_models"

    label: Mapped[str] = mapped_column(nullable=False)


def test_uuid_primary_key_mixin_defines_uuid_primary_key() -> None:
    id_column = TechnicalModel.__table__.c.id

    assert id_column.primary_key is True
    assert id_column.nullable is False
    assert id_column.default is not None
    assert id_column.type.python_type is UUID


def test_timestamp_mixin_defines_created_at_column() -> None:
    created_at_column = TechnicalModel.__table__.c.created_at

    assert isinstance(created_at_column.type, DateTime)
    assert created_at_column.type.timezone is True
    assert created_at_column.nullable is False
    assert created_at_column.server_default is not None


def test_timestamp_mixin_defines_updated_at_column() -> None:
    updated_at_column = TechnicalModel.__table__.c.updated_at

    assert isinstance(updated_at_column.type, DateTime)
    assert updated_at_column.type.timezone is True
    assert updated_at_column.nullable is False
    assert updated_at_column.server_default is not None
    assert updated_at_column.onupdate is not None
