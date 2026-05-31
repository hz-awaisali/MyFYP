"""Attachment schemas."""

import uuid
from datetime import datetime

from app.common.schemas import ORMBase


class AttachmentRead(ORMBase):
    id: uuid.UUID
    owner_type: str
    owner_id: uuid.UUID
    filename: str
    content_type: str
    size_bytes: int
    created_at: datetime


class AttachmentWithUrl(AttachmentRead):
    download_url: str
