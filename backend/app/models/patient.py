"""Patient SQLAlchemy ORM model."""

from datetime import date

from sqlalchemy import CheckConstraint, Date, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Patient(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Administrative patient record for the optometry practice."""

    __tablename__ = "patients"
    __table_args__ = (
        CheckConstraint("length(trim(first_name)) > 0", name="first_name_not_blank"),
        CheckConstraint("length(trim(last_name)) > 0", name="last_name_not_blank"),
        CheckConstraint(
            "preferred_language IN ('fr', 'nl', 'de', 'en')",
            name="preferred_language_supported",
        ),
        CheckConstraint("length(country_code) = 2", name="country_code_iso_3166_alpha_2"),
        Index("ix_patients_identity_lookup", "last_name", "first_name", "date_of_birth"),
    )

    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    preferred_language: Mapped[str] = mapped_column(
        String(5),
        nullable=False,
        default="fr",
        server_default="fr",
    )

    email: Mapped[str | None] = mapped_column(String(254))
    phone: Mapped[str | None] = mapped_column(String(32))
    street_line1: Mapped[str | None] = mapped_column(String(255))
    street_line2: Mapped[str | None] = mapped_column(String(255))
    postal_code: Mapped[str | None] = mapped_column(String(16))
    city: Mapped[str | None] = mapped_column(String(100))
    country_code: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
        default="BE",
        server_default="BE",
    )
