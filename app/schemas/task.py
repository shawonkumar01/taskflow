import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.task import TaskPriority, TaskStatus
from app.schemas.common import PageParams

SortField = Literal[
    "created_at",
    "-created_at",
    "updated_at",
    "-updated_at",
    "due_date",
    "-due_date",
    "title",
    "-title",
]


class TaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: date | None = None
    assignee_id: uuid.UUID | None = None


class TaskUpdate(BaseModel):
    """Partial update: only the fields that are sent are changed."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_date: date | None = None
    assignee_id: uuid.UUID | None = None

    @field_validator("title", "status", "priority")
    @classmethod
    def required_fields_cannot_be_null(cls, value: Any) -> Any:
        if value is None:
            raise ValueError("cannot be null")
        return value


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    due_date: date | None
    assignee_id: uuid.UUID | None
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


class TaskFilters(PageParams):
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    assignee_id: uuid.UUID | None = None
    due_after: date | None = Field(default=None, description="Due on or after this date.")
    due_before: date | None = Field(default=None, description="Due on or before this date.")
    sort: SortField = "-created_at"

    @model_validator(mode="after")
    def due_range_is_valid(self) -> "TaskFilters":
        if self.due_after and self.due_before and self.due_after > self.due_before:
            raise ValueError("due_after must not be later than due_before")
        return self
