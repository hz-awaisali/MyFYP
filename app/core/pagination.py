"""Pagination, sorting and search query parameters."""

from dataclasses import dataclass

from fastapi import Query


@dataclass
class PaginationParams:
    page: int
    size: int
    sort_by: str | None
    sort_order: str
    search: str | None

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size

    @property
    def limit(self) -> int:
        return self.size


def pagination_params(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: str | None = Query(None, description="Field name to sort by"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="asc or desc"),
    search: str | None = Query(None, description="Free-text search term"),
) -> PaginationParams:
    return PaginationParams(
        page=page, size=size, sort_by=sort_by, sort_order=sort_order, search=search
    )


def build_page_meta(total: int, page: int, size: int) -> dict:
    pages = (total + size - 1) // size if size else 0
    return {"total": total, "page": page, "size": size, "pages": pages}
