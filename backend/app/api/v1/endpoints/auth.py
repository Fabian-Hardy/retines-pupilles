"""Authentication API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_active_user, get_current_user
from app.core.security import create_access_token
from app.crud.user import authenticate_user, create_user, get_user_by_email
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import LoginRequest, TokenResponse, UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])

DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentActiveUser = Annotated[User, Depends(get_current_active_user)]


def _invalid_credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password",
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register_user_endpoint(
    user_in: UserCreate,
    session: DbSession,
) -> UserRead:
    """Register a user account."""

    existing_user = await get_user_by_email(session, str(user_in.email))
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = await create_user(session, user_in)
    await session.commit()

    return UserRead.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login_user_endpoint(
    login_in: LoginRequest,
    session: DbSession,
) -> TokenResponse:
    """Issue a Bearer access token for valid credentials."""

    user = await authenticate_user(
        session,
        email=str(login_in.email),
        password=login_in.password.get_secret_value(),
    )
    if user is None or not user.is_active:
        raise _invalid_credentials_exception()

    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout_user_endpoint(_current_user: CurrentUser) -> None:
    """Accept logout for a valid Bearer token."""

    return None


@router.get("/me", response_model=UserRead)
async def read_current_user_endpoint(current_user: CurrentActiveUser) -> UserRead:
    """Return the current authenticated user."""

    return UserRead.model_validate(current_user)
