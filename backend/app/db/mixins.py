"""Reusable SQLAlchemy ORM mixins."""

from sqlalchemy.orm import Mapped

from app.db.types import CreatedAt, UpdatedAt, UUIDPk


class UUIDPrimaryKeyMixin:
    """Add a UUID primary key column to a mapped model."""

    id: Mapped[UUIDPk]


class TimestampMixin:
    """Add technical creation and update timestamps to a mapped model."""

    created_at: Mapped[CreatedAt]
    updated_at: Mapped[UpdatedAt]
