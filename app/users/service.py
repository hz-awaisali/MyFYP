"""User management service: lifecycle, admin creation, profile updates."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import NotificationType, UserStatus
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.security import hash_password
from app.notifications.service import NotificationService
from app.roles.repository import RoleRepository
from app.users.models import User
from app.users.repository import UserRepository
from app.users.schemas import AdminCreateUser, UserStatusUpdate, UserUpdate


class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.users = UserRepository(session)
        self.roles = RoleRepository(session)
        self.notifications = NotificationService(session)

    async def get(self, user_id: uuid.UUID) -> User:
        user = await self.users.get_with_relations(user_id)
        if user is None:
            raise NotFoundError("User not found")
        return user

    async def list_users(self, **kwargs) -> tuple[list[User], int]:
        return await self.users.search(**kwargs)

    async def create_user(self, data: AdminCreateUser) -> User:
        if await self.users.get_by_email(data.email):
            raise ConflictError("An account with this email already exists")
        role = await self.roles.get_by_name(data.role_name)
        if role is None:
            raise ValidationError(f"Unknown role: {data.role_name}")

        user = User(
            email=data.email.lower(),
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
            phone=data.phone,
            status=data.status,
            role_id=role.id,
            department_id=data.department_id,
        )
        await self.users.add(user)
        await self.session.commit()
        return await self.users.get_with_relations(user.id)

    async def update_user(self, user_id: uuid.UUID, data: UserUpdate) -> User:
        user = await self.get(user_id)
        payload = data.model_dump(exclude_unset=True)
        for key, value in payload.items():
            setattr(user, key, value)
        await self.session.commit()
        return await self.users.get_with_relations(user.id)

    async def change_status(self, user_id: uuid.UUID, data: UserStatusUpdate) -> User:
        user = await self.get(user_id)
        previous = user.status
        user.status = data.status
        await self.session.flush()

        if previous != UserStatus.APPROVED and data.status == UserStatus.APPROVED:
            await self.notifications.notify(
                user_id=user.id,
                notification_type=NotificationType.ACCOUNT_APPROVED,
                title="Account approved",
                body="Your account has been approved. You can now log in.",
            )

        await self.session.commit()
        return await self.users.get_with_relations(user.id)
