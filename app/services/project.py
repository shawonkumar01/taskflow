import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
)
from app.models.project import Project
from app.models.project_member import ProjectMember, ProjectRole
from app.models.user import User, UserRole
from app.repositories.project import ProjectRepository
from app.repositories.task import TaskRepository
from app.repositories.user import UserRepository
from app.schemas.common import PageParams
from app.schemas.project import MemberAdd, ProjectCreate, ProjectUpdate
from app.services.access import load_project_access

PROJECT_NOT_FOUND = "Project not found."


class ProjectService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._projects = ProjectRepository(db)
        self._users = UserRepository(db)
        self._tasks = TaskRepository(db)

    def create(self, user: User, data: ProjectCreate) -> Project:
        project = Project(
            name=data.name, description=data.description, owner_id=user.id
        )
        project.members.append(ProjectMember(user_id=user.id, role=ProjectRole.OWNER))
        self._projects.add(project)
        self._db.commit()
        return self._reload(project.id)

    def list_projects(self, user: User, params: PageParams) -> tuple[list[Project], int]:
        if user.role == UserRole.ADMIN:
            return self._projects.list_all(params.offset, params.limit)
        return self._projects.list_for_member(user.id, params.offset, params.limit)

    def get(self, user: User, project_id: uuid.UUID) -> Project:
        return load_project_access(self._projects, user, project_id).project

    def update(self, user: User, project_id: uuid.UUID, data: ProjectUpdate) -> Project:
        access = load_project_access(self._projects, user, project_id)
        access.require_manage()
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(access.project, field, value)
        self._db.commit()
        return self._reload(project_id)

    def delete(self, user: User, project_id: uuid.UUID) -> None:
        access = load_project_access(self._projects, user, project_id)
        access.require_manage()
        self._projects.delete(access.project)
        self._db.commit()

    def add_member(
        self, user: User, project_id: uuid.UUID, data: MemberAdd
    ) -> ProjectMember:
        access = load_project_access(self._projects, user, project_id)
        access.require_manage()

        target = self._users.get_by_email(data.email)
        if target is None or not target.is_active:
            raise NotFoundError("User not found.")
        if access.has_member(target.id):
            raise ConflictError("User is already a member of this project.")

        member = ProjectMember(user=target, role=ProjectRole.MEMBER)
        access.project.members.append(member)
        try:
            self._db.commit()
        except IntegrityError:  # lost a race with a concurrent request
            self._db.rollback()
            raise ConflictError("User is already a member of this project.") from None
        return member

    def remove_member(
        self, user: User, project_id: uuid.UUID, member_user_id: uuid.UUID
    ) -> None:
        access = load_project_access(self._projects, user, project_id)
        access.require_manage()

        project = access.project
        member = next((m for m in project.members if m.user_id == member_user_id), None)
        if member is None:
            raise NotFoundError("Member not found.")
        if member.role == ProjectRole.OWNER:
            raise BadRequestError("The project owner cannot be removed.")

        self._tasks.unassign_user(project.id, member_user_id)
        project.members.remove(member)  # delete-orphan removes the row
        self._db.commit()

    def _reload(self, project_id: uuid.UUID) -> Project:
        project = self._projects.get_by_id(project_id)
        if project is None:  # cannot happen right after a successful commit
            raise NotFoundError(PROJECT_NOT_FOUND)
        return project
