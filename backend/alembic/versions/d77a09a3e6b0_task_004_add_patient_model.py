"""task 004 add patient model

Revision ID: d77a09a3e6b0
Revises: 1f9d0fab9699
Create Date: 2026-05-29
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d77a09a3e6b0"
down_revision: str | None = "1f9d0fab9699"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add patients table."""
    op.create_table(
        "patients",
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column(
            "preferred_language",
            sa.String(length=5),
            server_default="fr",
            nullable=False,
        ),
        sa.Column("email", sa.String(length=254), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("street_line1", sa.String(length=255), nullable=True),
        sa.Column("street_line2", sa.String(length=255), nullable=True),
        sa.Column("postal_code", sa.String(length=16), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column(
            "country_code",
            sa.String(length=2),
            server_default="BE",
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(country_code) = 2",
            name=op.f("ck_patients_country_code_iso_3166_alpha_2"),
        ),
        sa.CheckConstraint(
            "length(trim(first_name)) > 0",
            name=op.f("ck_patients_first_name_not_blank"),
        ),
        sa.CheckConstraint(
            "length(trim(last_name)) > 0",
            name=op.f("ck_patients_last_name_not_blank"),
        ),
        sa.CheckConstraint(
            "preferred_language IN ('fr', 'nl', 'de', 'en')",
            name=op.f("ck_patients_preferred_language_supported"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_patients")),
    )
    op.create_index(
        "ix_patients_identity_lookup",
        "patients",
        ["last_name", "first_name", "date_of_birth"],
        unique=False,
    )


def downgrade() -> None:
    """Drop patients table."""
    op.drop_index("ix_patients_identity_lookup", table_name="patients")
    op.drop_table("patients")
