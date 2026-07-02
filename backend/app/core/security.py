"""Password hashing and JWT helpers."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from authlib.jose import JoseError, JsonWebToken
from passlib.context import CryptContext

from app.core.config import settings

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_TYPE = "access"
PASSWORD_HASH_ROUNDS = 600_000

json_web_token = JsonWebToken([JWT_ALGORITHM])
password_context = CryptContext(
    schemes=["pbkdf2_sha256"],
    deprecated="auto",
    pbkdf2_sha256__rounds=PASSWORD_HASH_ROUNDS,
)


class InvalidTokenError(ValueError):
    """Raised when an access token cannot be trusted."""


def hash_password(password: str) -> str:
    """Return a password hash suitable for persisted credentials."""

    return str(password_context.hash(password))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return whether a plaintext password matches a stored hash."""

    try:
        return bool(password_context.verify(plain_password, hashed_password))
    except ValueError:
        return False


def create_access_token(
    subject: UUID | str,
    *,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token for a user subject."""

    issued_at = datetime.now(UTC)
    expires_at = issued_at + (
        expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    claims = {
        "sub": str(subject),
        "type": ACCESS_TOKEN_TYPE,
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
    }

    token = json_web_token.encode(
        {"alg": JWT_ALGORITHM},
        claims,
        settings.JWT_SECRET_KEY,
    )
    if isinstance(token, bytes):
        return token.decode("utf-8")
    return str(token)


def decode_access_token(token: str) -> UUID:
    """Validate an access token and return its user subject."""

    try:
        claims = json_web_token.decode(token, settings.JWT_SECRET_KEY)
        claims.validate()
    except JoseError as exc:
        raise InvalidTokenError("Invalid access token") from exc

    if claims.get("type") != ACCESS_TOKEN_TYPE:
        raise InvalidTokenError("Invalid token type")

    subject = claims.get("sub")
    if not isinstance(subject, str):
        raise InvalidTokenError("Invalid token subject")

    try:
        return UUID(subject)
    except ValueError as exc:
        raise InvalidTokenError("Invalid token subject") from exc


__all__ = [
    "InvalidTokenError",
    "PASSWORD_HASH_ROUNDS",
    "create_access_token",
    "decode_access_token",
    "hash_password",
    "verify_password",
]
