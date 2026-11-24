from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class PageParams(BaseModel):
    """Pagination query parameters. The limit is capped to protect the database."""

    model_config = ConfigDict(extra="forbid")

    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    limit: int
