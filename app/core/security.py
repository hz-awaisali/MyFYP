"""Password hashing and JWT token helpers."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def _create_token(
    subject: str,
    token_type: str,
    secret: str,
    expires_delta: timedelta,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "jti": str(uuid.uuid4()),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, secret, algorithm=settings.JWT_ALGORITHM)


def create_access_token(subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    return _create_token(
        subject,
        ACCESS_TOKEN_TYPE,
        settings.JWT_SECRET_KEY,
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        extra_claims,
    )


def create_refresh_token(subject: str) -> str:
    return _create_token(
        subject,
        REFRESH_TOKEN_TYPE,
        settings.JWT_REFRESH_SECRET_KEY,
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str, token_type: str) -> dict[str, Any]:
    """Decode and validate a JWT. Raises JWTError on failure."""
    secret = (
        settings.JWT_SECRET_KEY
        if token_type == ACCESS_TOKEN_TYPE
        else settings.JWT_REFRESH_SECRET_KEY
    )
    payload = jwt.decode(token, secret, algorithms=[settings.JWT_ALGORITHM])
    if payload.get("type") != token_type:
        raise JWTError("Invalid token type")
    return payload
