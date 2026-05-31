"""User repository."""

from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from app.common.enums import UserStatus
from app.common.repository import BaseRepository
from app.users.models import StudentProfile, User


class UserRepository(BaseRepository[User]):
    model = User

    def _with_relations(self, stmt):
        return stmt.options(
            selectinload(User.role),
            selectinload(User.student_profile),
        )

    async def get_with_relations(self, id_) -> User | None:
        stmt = self._with_relations(select(User).where(User.id == id_))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        stmt = self._with_relations(select(User).where(User.email == email.lower()))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def search(
        self,
        *,
        offset: int,
        limit: int,
        status: UserStatus | None = None,
        role_id=None,
        department_id=None,
        term: str | None = None,
    ) -> tuple[list[User], int]:
        from sqlalchemy import func

        conditions = []
        if status is not None:
            conditions.append(User.status == status)
        if role_id is not None:
            conditions.append(User.role_id == role_id)
        if department_id is not None:
            conditions.append(User.department_id == department_id)
        if term:
            like = f"%{term}%"
            conditions.append(or_(User.full_name.ilike(like), User.email.ilike(like)))

        base = select(User)
        count_stmt = select(func.count()).select_from(User)
        for cond in conditions:
            base = base.where(cond)
            count_stmt = count_stmt.where(cond)

        base = self._with_relations(base).order_by(User.created_at.desc()).offset(offset).limit(limit)
        items = list((await self.session.execute(base)).scalars().all())
        total = int((await self.session.execute(count_stmt)).scalar_one())
        return items, total


class StudentProfileRepository(BaseRepository[StudentProfile]):
    model = StudentProfile

    async def get_by_user(self, user_id) -> StudentProfile | None:
        return await self.get_by(user_id=user_id)

    async def get_by_registration(self, registration_number: str) -> StudentProfile | None:
        return await self.get_by(registration_number=registration_number)
