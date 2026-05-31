"""Authentication service: registration, login, token refresh."""

import uuid

from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import RegisterRequest, TokenPair
from app.common.enums import RoleName, UserStatus
from app.core.exceptions import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.core.security import (
    REFRESH_TOKEN_TYPE,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.roles.repository import RoleRepository
from app.users.models import StudentProfile, User
from app.users.repository import StudentProfileRepository, UserRepository


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.users = UserRepository(session)
        self.roles = RoleRepository(session)
        self.profiles = StudentProfileRepository(session)

    def _issue_tokens(self, user: User) -> TokenPair:
        claims = {"role": user.role.name if user.role else None}
        return TokenPair(
            access_token=create_access_token(str(user.id), extra_claims=claims),
            refresh_token=create_refresh_token(str(user.id)),
        )

    async def register_student(self, data: RegisterRequest) -> User:
        """Public registration always creates a PENDING student account."""
        existing = await self.users.get_by_email(data.email)
        if existing:
            raise ConflictError("An account with this email already exists")

        if await self.profiles.get_by_registration(data.registration_number):
            raise ConflictError("This registration number is already in use")

        student_role = await self.roles.get_by_name(RoleName.STUDENT.value)
        if student_role is None:
            raise NotFoundError("Student role is not configured; run the seed script")

        program_uuid: uuid.UUID | None = None
        if data.program_id:
            try:
                program_uuid = uuid.UUID(data.program_id)
            except ValueError as exc:
                raise ValidationError("program_id must be a valid UUID") from exc

        user = User(
            email=data.email.lower(),
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
            phone=data.phone,
            status=UserStatus.PENDING,
            role_id=student_role.id,
        )
        await self.users.add(user)

        profile = StudentProfile(
            user_id=user.id,
            registration_number=data.registration_number,
            program_id=program_uuid,
        )
        await self.profiles.add(profile)

        await self.session.commit()
        return await self.users.get_with_relations(user.id)

    async def authenticate(self, email: str, password: str) -> tuple[User, TokenPair]:
        user = await self.users.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise AuthenticationError("Invalid email or password")
        if not user.is_active:
            raise AuthenticationError("Account is inactive")
        if user.status == UserStatus.PENDING:
            raise AuthenticationError("Account is pending approval by an administrator")
        if user.status != UserStatus.APPROVED:
            raise AuthenticationError(f"Account is {user.status.value}")
        return user, self._issue_tokens(user)

    async def refresh(self, refresh_token: str) -> TokenPair:
        try:
            payload = decode_token(refresh_token, REFRESH_TOKEN_TYPE)
            user_id = uuid.UUID(payload["sub"])
        except (JWTError, KeyError, ValueError) as exc:
            raise AuthenticationError("Invalid or expired refresh token") from exc

        user = await self.users.get_with_relations(user_id)
        if user is None or user.status != UserStatus.APPROVED or not user.is_active:
            raise AuthenticationError("Account is not eligible for token refresh")
        return self._issue_tokens(user)
