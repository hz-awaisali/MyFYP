"""Attachment repository."""

import uuid

from sqlalchemy import select

from app.attachments.models import Attachment
from app.common.repository import BaseRepository


class AttachmentRepository(BaseRepository[Attachment]):
    model = Attachment

    async def list_for_owner(self, owner_type: str, owner_id: uuid.UUID) -> list[Attachment]:
        stmt = (
            select(Attachment)
            .where(Attachment.owner_type == owner_type, Attachment.owner_id == owner_id)
            .order_by(Attachment.created_at)
        )
        return list((await self.session.execute(stmt)).scalars().all())
