import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.models.project import Project
from app.models.project_member import ProjectMember


class ProjectRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def add(self, project: Project) -> Project:
        self._db.add(project)
        self._db.flush()
        return project

    def get_by_id(self, project_id: uuid.UUID) -> Project | None:
        """Loads the project with its members (and their users) in one go."""
        stmt = (
            select(Project)
            .where(Project.id == project_id)
            .options(selectinload(Project.members).selectinload(ProjectMember.user))
            .execution_options(populate_existing=True)
        )
        return self._db.execute(stmt).scalar_one_or_none()

    def list_for_member(
        self, user_id: uuid.UUID, offset: int, limit: int
    ) -> tuple[list[Project], int]:
        stmt = (
            select(Project)
            .join(ProjectMember, ProjectMember.project_id == Project.id)
            .where(ProjectMember.user_id == user_id)
        )
        return self._paginate(stmt, offset, limit)

    def list_all(self, offset: int, limit: int) -> tuple[list[Project], int]:
        return self._paginate(select(Project), offset, limit)

    def delete(self, project: Project) -> None:
        self._db.delete(project)
        self._db.flush()

    def _paginate(
        self, stmt: Select[tuple[Project]], offset: int, limit: int
    ) -> tuple[list[Project], int]:
        total = self._db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        items = self._db.scalars(
            stmt.order_by(Project.created_at.desc(), Project.id).offset(offset).limit(limit)
        ).all()
        return list(items), total
