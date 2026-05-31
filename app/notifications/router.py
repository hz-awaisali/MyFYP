"""Notification endpoints + WebSocket stream."""

import uuid

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas import Message, Page
from app.core.database import AsyncSessionLocal, get_db
from app.core.deps import CurrentUser
from app.core.pagination import PaginationParams, build_page_meta, pagination_params
from app.core.security import ACCESS_TOKEN_TYPE, decode_token
from app.core.websocket import manager
from app.notifications.schemas import NotificationRead_, UnreadCount
from app.notifications.service import NotificationService
from app.users.repository import UserRepository

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=Page[NotificationRead_])
async def list_notifications(
    current_user: CurrentUser,
    pagination: PaginationParams = Depends(pagination_params),
    unread_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    items, total = await NotificationService(db).list_for_user(
        current_user.id,
        offset=pagination.offset,
        limit=pagination.limit,
        unread_only=unread_only,
    )
    return Page(items=items, meta=build_page_meta(total, pagination.page, pagination.size))


@router.get("/unread-count", response_model=UnreadCount)
async def unread_count(current_user: CurrentUser, db: AsyncSession = Depends(get_db)):
    count = await NotificationService(db).unread_count(current_user.id)
    return UnreadCount(unread=count)


@router.post("/{notification_id}/read", response_model=NotificationRead_)
async def mark_read(
    notification_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    return await NotificationService(db).mark_read(current_user.id, notification_id)


@router.post("/read-all", response_model=Message)
async def mark_all_read(current_user: CurrentUser, db: AsyncSession = Depends(get_db)):
    count = await NotificationService(db).mark_all_read(current_user.id)
    return Message(message=f"Marked {count} notification(s) as read")


@router.websocket("/ws")
async def notifications_ws(websocket: WebSocket, token: str = Query(...)):
    """Realtime notification stream. Authenticate with ?token=<access_token>."""
    try:
        payload = decode_token(token, ACCESS_TOKEN_TYPE)
        user_id = uuid.UUID(payload["sub"])
    except (JWTError, KeyError, ValueError):
        await websocket.close(code=1008)
        return

    async with AsyncSessionLocal() as session:
        user = await UserRepository(session).get(user_id)
        if user is None or not user.is_active:
            await websocket.close(code=1008)
            return

    await manager.connect(user_id, websocket)
    try:
        while True:
            # Keep the connection alive; inbound messages are ignored for now.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
