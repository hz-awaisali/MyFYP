"""Attachment service: validation, storage, presigned URLs."""

import uuid

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.attachments.models import Attachment
from app.attachments.repository import AttachmentRepository
from app.attachments.storage import get_storage
from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationError


class AttachmentService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = AttachmentRepository(session)
        self.storage = get_storage()

    def _validate(self, filename: str, size: int) -> str:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in settings.allowed_extensions_set:
            raise ValidationError(
                f"File type '.{ext}' is not allowed. Allowed: {sorted(settings.allowed_extensions_set)}"
            )
        if size > settings.max_upload_bytes:
            raise ValidationError(
                f"File exceeds the maximum size of {settings.MAX_UPLOAD_SIZE_MB} MB"
            )
        return ext

    async def upload(
        self,
        *,
        file: UploadFile,
        owner_type: str,
        owner_id: uuid.UUID,
        uploaded_by: uuid.UUID | None,
        commit: bool = True,
    ) -> Attachment:
        data = await file.read()
        ext = self._validate(file.filename or "file", len(data))

        key = f"{owner_type}/{owner_id}/{uuid.uuid4()}.{ext}"
        content_type = file.content_type or "application/octet-stream"
        self.storage.save(key, data, content_type)

        attachment = Attachment(
            owner_type=owner_type,
            owner_id=owner_id,
            filename=file.filename or key,
            content_type=content_type,
            size_bytes=len(data),
            storage_backend=settings.STORAGE_BACKEND.lower(),
            storage_key=key,
            bucket=settings.B2_BUCKET_NAME or None,
            uploaded_by=uploaded_by,
        )
        await self.repo.add(attachment)
        if commit:
            await self.session.commit()
        return attachment

    async def list_for_owner(self, owner_type: str, owner_id: uuid.UUID) -> list[Attachment]:
        return await self.repo.list_for_owner(owner_type, owner_id)

    def download_url(self, attachment: Attachment) -> str:
        return self.storage.url(attachment.storage_key)

    async def get(self, attachment_id: uuid.UUID) -> Attachment:
        attachment = await self.repo.get(attachment_id)
        if attachment is None:
            raise NotFoundError("Attachment not found")
        return attachment

    async def delete(self, attachment_id: uuid.UUID) -> None:
        attachment = await self.get(attachment_id)
        self.storage.delete(attachment.storage_key)
        await self.repo.delete(attachment)
        await self.session.commit()
