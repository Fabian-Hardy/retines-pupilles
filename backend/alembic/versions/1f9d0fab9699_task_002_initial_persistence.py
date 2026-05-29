"""task 002 initial persistence

Revision ID: 1f9d0fab9699
Revises:
Create Date: 2026-05-29 18:36:03.013543
"""

from __future__ import annotations

revision: str = "1f9d0fab9699"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Apply initial persistence baseline."""
    pass


def downgrade() -> None:
    """Rollback initial persistence baseline."""
    pass
