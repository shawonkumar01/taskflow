import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, PermissionDeniedError
from app.models.task import Task
from app.models.user import User
from app.repositories.project import ProjectRepository
from app.repositories.task import TaskRepository
from app.schemas.task import TaskCreate, TaskFilters, TaskUpdate
from app.services.access import ProjectAccess, load_project_access

TASK_NOT_FOUND = "Task not found."


class TaskService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._tasks = TaskRepository(db)
        self._projects = ProjectRepository(db)

    def create(self, user: User, project_id: uuid.UUID, data: TaskCreate) -> Task:
        access = load_project_access(self._projects, user, project_id)
        self._validate_assignee(access, data.assignee_id)

        task = Task(
            project_id=project_id,
            title=data.title,
            description=data.description,
            priority=data.priority,
            due_date=data.due_date,
            assignee_id=data.assignee_id,
            created_by=user.id,
        )
        self._tasks.add(task)
        self._db.commit()
        self._db.refresh(task)
        return task

    def list_tasks(
        self, user: User, project_id: uuid.UUID, filters: TaskFilters
    ) -> tuple[list[Task], int]:
        load_project_access(self._projects, user, project_id)
        return self._tasks.list_for_project(project_id, filters)

    def get(self, user: User, task_id: uuid.UUID) -> Task:
        task, _ = self._load(user, task_id)
        return task

    def update(self, user: User, task_id: uuid.UUID, data: TaskUpdate) -> Task:
        task, access = self._load(user, task_id)
        if not (access.can_manage or user.id in (task.created_by, task.assignee_id)):
            raise PermissionDeniedError(
                "Only the project owner, the task creator or the assignee can edit this task."
            )

        changes = data.model_dump(exclude_unset=True)
        self._validate_assignee(access, changes.get("assignee_id"))
        for field, value in changes.items():
            setattr(task, field, value)
        self._db.commit()
        self._db.refresh(task)
        return task

    def delete(self, user: User, task_id: uuid.UUID) -> None:
        task, access = self._load(user, task_id)
        if not (access.can_manage or user.id == task.created_by):
            raise PermissionDeniedError(
                "Only the project owner or the task creator can delete this task."
            )
        self._tasks.delete(task)
        self._db.commit()

    # --- helpers -------------------------------------------------------------

    def _load(self, user: User, task_id: uuid.UUID) -> tuple[Task, ProjectAccess]:
        task = self._tasks.get_by_id(task_id)
        if task is None:
            from app.core.exceptions import NotFoundError

            raise NotFoundError(TASK_NOT_FOUND)
        access = load_project_access(
            self._projects, user, task.project_id, not_found_message=TASK_NOT_FOUND
        )
        return task, access

    @staticmethod
    def _validate_assignee(access: ProjectAccess, assignee_id: uuid.UUID | None) -> None:
        if assignee_id is not None and not access.has_member(assignee_id):
            raise BadRequestError("The assignee must be a member of the project.")
