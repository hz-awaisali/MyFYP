"""Shared Pydantic schema helpers (response envelopes, pagination)."""

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ORMBase(BaseModel):
    """Base schema with ORM mode enabled."""

    model_config = {"from_attributes": True}


class Message(BaseModel):
    success: bool = True
    message: str


class PageMeta(BaseModel):
    total: int
    page: int
    size: int
    pages: int


class Page(BaseModel, Generic[T]):
    items: list[T]
    meta: PageMeta
