import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.project_member import ProjectRole
from app.schemas.auth import NormalizedEmail
from app.schemas.user import UserSummary


class ProjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)


class ProjectUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("name")
    @classmethod
    def name_cannot_be_null(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("name cannot be null")
        return value


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    owner_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class MemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user: UserSummary
    role: ProjectRole
    joined_at: datetime


class ProjectDetail(ProjectRead):
    members: list[MemberRead]


class MemberAdd(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: NormalizedEmail
