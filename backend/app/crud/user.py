"""CRUD helpers for User resources."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import UserCreate


def normalize_email(email: str) -> str:
    """Normalize an email address before lookup or persistence."""

    return email.strip().lower()


async def create_user(session: AsyncSession, user_in: UserCreate) -> User:
    """Create a user account without committing the transaction."""

    user = User(
        email=normalize_email(str(user_in.email)),
        hashed_password=hash_password(user_in.password),
        full_name=user_in.full_name,
    )

    session.add(user)
    await session.flush()
    await session.refresh(user)

    return user


async def get_user(session: AsyncSession, user_id: UUID) -> User | None:
    """Return a user by ID, or None when no matching row exists."""

    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    """Return a user by normalized email, or None when absent."""

    result = await session.execute(select(User).where(User.email == normalize_email(email)))
    return result.scalar_one_or_none()


async def authenticate_user(
    session: AsyncSession,
    *,
    email: str,
    password: str,
) -> User | None:
    """Return a user when credentials are valid."""

    user = await get_user_by_email(session, email)
    if user is None:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user


__all__ = [
    "authenticate_user",
    "create_user",
    "get_user",
    "get_user_by_email",
    "normalize_email",
]
