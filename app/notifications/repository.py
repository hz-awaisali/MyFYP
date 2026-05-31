"""Notification repository."""

import uuid

from sqlalchemy import func, select

from app.common.repository import BaseRepository
from app.notifications.models import Notification


class NotificationRepository(BaseRepository[Notification]):
    model = Notification

    async def list_for_user(
        self, user_id: uuid.UUID, *, offset: int, limit: int, unread_only: bool = False
    ) -> tuple[list[Notification], int]:
        conditions = [Notification.user_id == user_id]
        if unread_only:
            conditions.append(Notification.is_read.is_(False))

        stmt = select(Notification)
        count_stmt = select(func.count()).select_from(Notification)
        for cond in conditions:
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)

        stmt = stmt.order_by(Notification.created_at.desc()).offset(offset).limit(limit)
        items = list((await self.session.execute(stmt)).scalars().all())
        total = int((await self.session.execute(count_stmt)).scalar_one())
        return items, total

    async def unread_count(self, user_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == user_id, Notification.is_read.is_(False))
        )
        return int((await self.session.execute(stmt)).scalar_one())
