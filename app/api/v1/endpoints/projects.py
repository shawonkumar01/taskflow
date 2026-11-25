import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, ProjectServiceDep
from app.core.rate_limit import member_rate_limit
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.schemas.common import Page, PageParams
from app.schemas.project import (
    MemberAdd,
    MemberRead,
    ProjectCreate,
    ProjectDetail,
    ProjectRead,
    ProjectUpdate,
)

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectDetail, status_code=status.HTTP_201_CREATED)
def create_project(
    data: ProjectCreate, current_user: CurrentUser, service: ProjectServiceDep
) -> Project:
    return service.create(current_user, data)


@router.get("", response_model=Page[ProjectRead])
def list_projects(
    params: Annotated[PageParams, Query()],
    current_user: CurrentUser,
    service: ProjectServiceDep,
) -> Page[ProjectRead]:
    projects, total = service.list_projects(current_user, params)
    return Page[ProjectRead](
        items=[ProjectRead.model_validate(p) for p in projects],
        total=total,
        page=params.page,
        limit=params.limit,
    )


@router.get("/{project_id}", response_model=ProjectDetail)
def get_project(
    project_id: uuid.UUID, current_user: CurrentUser, service: ProjectServiceDep
) -> Project:
    return service.get(current_user, project_id)


@router.patch("/{project_id}", response_model=ProjectDetail)
def update_project(
    project_id: uuid.UUID,
    data: ProjectUpdate,
    current_user: CurrentUser,
    service: ProjectServiceDep,
) -> Project:
    return service.update(current_user, project_id, data)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: uuid.UUID, current_user: CurrentUser, service: ProjectServiceDep
) -> None:
    service.delete(current_user, project_id)


@router.post(
    "/{project_id}/members",
    response_model=MemberRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(member_rate_limit)],  # members are looked up by email
)
def add_member(
    project_id: uuid.UUID,
    data: MemberAdd,
    current_user: CurrentUser,
    service: ProjectServiceDep,
) -> ProjectMember:
    return service.add_member(current_user, project_id, data)


@router.delete(
    "/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT
)
def remove_member(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: CurrentUser,
    service: ProjectServiceDep,
) -> None:
    service.remove_member(current_user, project_id, user_id)
