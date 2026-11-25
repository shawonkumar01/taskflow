import uuid

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.task import Task
from app.schemas.task import TaskFilters

SORT_COLUMNS = {
    "created_at": Task.created_at,
    "updated_at": Task.updated_at,
    "due_date": Task.due_date,
    "title": Task.title,
}


class TaskRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def add(self, task: Task) -> Task:
        self._db.add(task)
        self._db.flush()
        return task

    def get_by_id(self, task_id: uuid.UUID) -> Task | None:
        return self._db.get(Task, task_id)

    def delete(self, task: Task) -> None:
        self._db.delete(task)
        self._db.flush()

    def list_for_project(
        self, project_id: uuid.UUID, filters: TaskFilters
    ) -> tuple[list[Task], int]:
        stmt = select(Task).where(Task.project_id == project_id)
        if filters.status is not None:
            stmt = stmt.where(Task.status == filters.status)
        if filters.priority is not None:
            stmt = stmt.where(Task.priority == filters.priority)
        if filters.assignee_id is not None:
            stmt = stmt.where(Task.assignee_id == filters.assignee_id)
        if filters.due_after is not None:
            stmt = stmt.where(Task.due_date >= filters.due_after)
        if filters.due_before is not None:
            stmt = stmt.where(Task.due_date <= filters.due_before)

        total = self._db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

        column = SORT_COLUMNS[filters.sort.lstrip("-")]
        ordering = column.desc() if filters.sort.startswith("-") else column.asc()
        if column is Task.due_date:
            ordering = ordering.nulls_last()

        items = self._db.scalars(
            stmt.order_by(ordering, Task.id).offset(filters.offset).limit(filters.limit)
        ).all()
        return list(items), total

    def unassign_user(self, project_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """Clear the assignee on a project's tasks, e.g. when a member is removed."""
        self._db.execute(
            update(Task)
            .where(Task.project_id == project_id, Task.assignee_id == user_id)
            .values(assignee_id=None)
        )
