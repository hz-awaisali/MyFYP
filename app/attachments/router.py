"""Attachment endpoints."""

import uuid

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.attachments.models import Attachment
from app.attachments.schemas import AttachmentRead, AttachmentWithUrl
from app.attachments.service import AttachmentService
from app.attachments.storage import LocalStorage, get_storage
from app.common.schemas import Message
from app.core.database import get_db
from app.core.deps import CurrentUser
from app.core.exceptions import NotFoundError

router = APIRouter(prefix="/attachments", tags=["Attachments"])


def _with_url(service: AttachmentService, attachment: Attachment) -> AttachmentWithUrl:
    base = AttachmentRead.model_validate(attachment).model_dump()
    return AttachmentWithUrl(**base, download_url=service.download_url(attachment))


@router.post("", response_model=AttachmentWithUrl, status_code=201)
async def upload_attachment(
    current_user: CurrentUser,
    owner_type: str = Query(..., description="e.g. 'application'"),
    owner_id: uuid.UUID = Query(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    service = AttachmentService(db)
    attachment = await service.upload(
        file=file, owner_type=owner_type, owner_id=owner_id, uploaded_by=current_user.id
    )
    return _with_url(service, attachment)


@router.get("/{attachment_id}", response_model=AttachmentWithUrl)
async def get_attachment(
    attachment_id: uuid.UUID,
    _: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    service = AttachmentService(db)
    attachment = await service.get(attachment_id)
    return _with_url(service, attachment)


@router.delete("/{attachment_id}", response_model=Message)
async def delete_attachment(
    attachment_id: uuid.UUID,
    _: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    await AttachmentService(db).delete(attachment_id)
    return Message(message="Attachment deleted")


@router.get("/local/{key:path}")
async def download_local(key: str, _: CurrentUser):
    """Serve files when STORAGE_BACKEND=local (B2 uses presigned URLs instead)."""
    storage = get_storage()
    if not isinstance(storage, LocalStorage):
        raise NotFoundError("Local download is not enabled")
    try:
        data = storage.read(key)
    except FileNotFoundError as exc:
        raise NotFoundError("File not found") from exc
    return Response(content=data, media_type="application/octet-stream")
