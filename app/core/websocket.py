"""WebSocket connection manager for realtime notifications and dashboard updates.

The system is realtime-capable even without a frontend: services call
``manager.send_to_user(...)`` which silently no-ops when nobody is connected.
"""

import uuid
from collections import defaultdict

from fastapi import WebSocket

from app.core.logging import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        # user_id -> set of active sockets (a user may have multiple devices)
        self._connections: dict[uuid.UUID, set[WebSocket]] = defaultdict(set)

    async def connect(self, user_id: uuid.UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[user_id].add(websocket)
        logger.debug("WebSocket connected for user %s", user_id)

    def disconnect(self, user_id: uuid.UUID, websocket: WebSocket) -> None:
        conns = self._connections.get(user_id)
        if conns and websocket in conns:
            conns.discard(websocket)
            if not conns:
                self._connections.pop(user_id, None)
        logger.debug("WebSocket disconnected for user %s", user_id)

    async def send_to_user(self, user_id: uuid.UUID, message: dict) -> None:
        """Push a JSON message to all of a user's connected sockets."""
        for ws in list(self._connections.get(user_id, set())):
            try:
                await ws.send_json(message)
            except Exception:  # noqa: BLE001 - drop dead sockets
                self.disconnect(user_id, ws)

    async def broadcast(self, message: dict) -> None:
        for user_id in list(self._connections.keys()):
            await self.send_to_user(user_id, message)


manager = ConnectionManager()
