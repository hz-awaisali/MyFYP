"""System setting schemas."""

import uuid

from pydantic import BaseModel

from app.common.schemas import ORMBase


class SettingRead(ORMBase):
    id: uuid.UUID
    key: str
    value: str | None = None
    description: str | None = None


class SettingUpsert(BaseModel):
    key: str
    value: str | None = None
    description: str | None = None
