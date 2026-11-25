import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, TaskServiceDep
from app.models.task import Task
from app.schemas.common import Page
from app.schemas.task import TaskCreate, TaskFilters, TaskRead, TaskUpdate

# Collection routes live under a project; item routes are addressed by task id.
project_tasks_router = APIRouter(
    prefix="/projects/{project_id}/tasks", tags=["tasks"]
)
router = APIRouter(prefix="/tasks", tags=["tasks"])


@project_tasks_router.post(
    "", response_model=TaskRead, status_code=status.HTTP_201_CREATED
)
def create_task(
    project_id: uuid.UUID,
    data: TaskCreate,
    current_user: CurrentUser,
    service: TaskServiceDep,
) -> Task:
    return service.create(current_user, project_id, data)


@project_tasks_router.get("", response_model=Page[TaskRead])
def list_tasks(
    project_id: uuid.UUID,
    filters: Annotated[TaskFilters, Query()],
    current_user: CurrentUser,
    service: TaskServiceDep,
) -> Page[TaskRead]:
    tasks, total = service.list_tasks(current_user, project_id, filters)
    return Page[TaskRead](
        items=[TaskRead.model_validate(task) for task in tasks],
        total=total,
        page=filters.page,
        limit=filters.limit,
    )


@router.get("/{task_id}", response_model=TaskRead)
def get_task(
    task_id: uuid.UUID, current_user: CurrentUser, service: TaskServiceDep
) -> Task:
    return service.get(current_user, task_id)


@router.patch("/{task_id}", response_model=TaskRead)
def update_task(
    task_id: uuid.UUID,
    data: TaskUpdate,
    current_user: CurrentUser,
    service: TaskServiceDep,
) -> Task:
    return service.update(current_user, task_id, data)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: uuid.UUID, current_user: CurrentUser, service: TaskServiceDep
) -> None:
    service.delete(current_user, task_id)
