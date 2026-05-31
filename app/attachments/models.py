"""Attachment model."""

import uuid

from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.common.models import Base, TimestampMixin, UUIDMixin


class Attachment(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "attachments"

    # Polymorphic owner (e.g. "application"); owner_id references that entity.
    owner_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True, nullable=False)

    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)

    storage_backend: Mapped[str] = mapped_column(String(20), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    bucket: Mapped[str | None] = mapped_column(String(120))

    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
