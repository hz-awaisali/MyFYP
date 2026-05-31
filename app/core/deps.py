"""Shared FastAPI dependencies: current user, role and permission guards."""

import uuid
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import UserStatus
from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.security import ACCESS_TOKEN_TYPE, decode_token
from app.users.models import User
from app.users.repository import UserRepository

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login", auto_error=False
)


async def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_db),
) -> User:
    if not token:
        raise AuthenticationError("Not authenticated")
    try:
        payload = decode_token(token, ACCESS_TOKEN_TYPE)
        user_id = uuid.UUID(payload["sub"])
    except (JWTError, KeyError, ValueError) as exc:
        raise AuthenticationError("Invalid or expired token") from exc

    user = await UserRepository(db).get_with_relations(user_id)
    if user is None:
        raise AuthenticationError("User no longer exists")
    if not user.is_active:
        raise AuthenticationError("Account is inactive")
    if user.status != UserStatus.APPROVED:
        raise AuthenticationError(f"Account is {user.status.value}, access denied")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_permissions(*required: str):
    """Dependency factory enforcing that the current user has all given permissions.

    Super admins bypass all checks.
    """

    async def _guard(user: CurrentUser) -> User:
        if user.is_super_admin:
            return user
        missing = set(required) - user.permissions
        if missing:
            raise PermissionDeniedError(
                f"Missing required permission(s): {', '.join(sorted(missing))}"
            )
        return user

    return _guard


def require_any_permission(*options: str):
    """Dependency factory: user must have at least one of the given permissions."""

    async def _guard(user: CurrentUser) -> User:
        if user.is_super_admin or (set(options) & user.permissions):
            return user
        raise PermissionDeniedError(
            f"Requires one of: {', '.join(sorted(options))}"
        )

    return _guard


def get_client_ip(request: Request) -> str | None:
    return getattr(request.state, "client_ip", None)
