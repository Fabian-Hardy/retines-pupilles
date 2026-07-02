"""Typed SQLAlchemy column conventions shared by ORM models."""

from datetime import datetime
from typing import Annotated
from uuid import UUID, uuid4

from sqlalchemy import DateTime, func
from sqlalchemy.orm import mapped_column
from sqlalchemy.types import Uuid

UUIDPk = Annotated[
    UUID,
    mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    ),
]

CreatedAt = Annotated[
    datetime,
    mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
]

UpdatedAt = Annotated[
    datetime,
    mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    ),
]
