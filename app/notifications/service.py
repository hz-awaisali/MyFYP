"""Notification service: persist + realtime push via WebSocket."""

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import NotificationType
from app.core.exceptions import NotFoundError
from app.core.websocket import manager
from app.notifications.models import Notification
from app.notifications.repository import NotificationRepository


class NotificationService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = NotificationRepository(session)

    async def notify(
        self,
        *,
        user_id: uuid.UUID,
        notification_type: NotificationType,
        title: str,
        body: str | None = None,
        department_id: uuid.UUID | None = None,
        reference_type: str | None = None,
        reference_id: uuid.UUID | None = None,
    ) -> Notification:
        """Persist a notification and push it over WebSocket (best-effort)."""
        notification = Notification(
            user_id=user_id,
            department_id=department_id,
            type=notification_type,
            title=title,
            body=body,
            reference_type=reference_type,
            reference_id=reference_id,
        )
        await self.repo.add(notification)
        # Flush only; the caller owns the transaction/commit.

        await manager.send_to_user(
            user_id,
            {
                "event": "notification",
                "data": {
                    "id": str(notification.id),
                    "type": notification_type.value,
                    "title": title,
                    "body": body,
                    "reference_type": reference_type,
                    "reference_id": str(reference_id) if reference_id else None,
                },
            },
        )
        return notification

    async def list_for_user(self, user_id, *, offset, limit, unread_only=False):
        return await self.repo.list_for_user(
            user_id, offset=offset, limit=limit, unread_only=unread_only
        )

    async def unread_count(self, user_id) -> int:
        return await self.repo.unread_count(user_id)

    async def mark_read(self, user_id: uuid.UUID, notification_id: uuid.UUID) -> Notification:
        notification = await self.repo.get(notification_id)
        if notification is None or notification.user_id != user_id:
            raise NotFoundError("Notification not found")
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = datetime.now(timezone.utc)
            await self.session.commit()
        return notification

    async def mark_all_read(self, user_id: uuid.UUID) -> int:
        items, _ = await self.repo.list_for_user(
            user_id, offset=0, limit=1000, unread_only=True
        )
        now = datetime.now(timezone.utc)
        for n in items:
            n.is_read = True
            n.read_at = now
        await self.session.commit()
        return len(items)
