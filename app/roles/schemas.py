"""Role and permission schemas."""

import uuid

from app.common.schemas import ORMBase


class PermissionRead(ORMBase):
    id: uuid.UUID
    code: str
    description: str | None = None


class RoleRead(ORMBase):
    id: uuid.UUID
    name: str
    description: str | None = None
    is_system: bool
    permissions: list[PermissionRead] = []
