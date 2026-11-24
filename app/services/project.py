import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from app.models.project import Project
from app.models.project_member import ProjectMember, ProjectRole
from app.models.user import User, UserRole
from app.repositories.project import ProjectRepository
from app.repositories.user import UserRepository
from app.schemas.common import PageParams
from app.schemas.project import MemberAdd, ProjectCreate, ProjectUpdate

PROJECT_NOT_FOUND = "Project not found."


class ProjectService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._projects = ProjectRepository(db)
        self._users = UserRepository(db)

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
        project, _ = self._get_visible(user, project_id)
        return project

    def update(self, user: User, project_id: uuid.UUID, data: ProjectUpdate) -> Project:
        project, role = self._get_visible(user, project_id)
        self._require_manage(user, role)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(project, field, value)
        self._db.commit()
        return self._reload(project.id)

    def delete(self, user: User, project_id: uuid.UUID) -> None:
        project, role = self._get_visible(user, project_id)
        self._require_manage(user, role)
        self._projects.delete(project)
        self._db.commit()

    def add_member(
        self, user: User, project_id: uuid.UUID, data: MemberAdd
    ) -> ProjectMember:
        project, role = self._get_visible(user, project_id)
        self._require_manage(user, role)

        target = self._users.get_by_email(data.email)
        if target is None or not target.is_active:
            raise NotFoundError("User not found.")
        if any(member.user_id == target.id for member in project.members):
            raise ConflictError("User is already a member of this project.")

        member = ProjectMember(user=target, role=ProjectRole.MEMBER)
        project.members.append(member)
        try:
            self._db.commit()
        except IntegrityError:  # lost a race with a concurrent request
            self._db.rollback()
            raise ConflictError("User is already a member of this project.") from None
        return member

    def remove_member(
        self, user: User, project_id: uuid.UUID, member_user_id: uuid.UUID
    ) -> None:
        project, role = self._get_visible(user, project_id)
        self._require_manage(user, role)

        member = next((m for m in project.members if m.user_id == member_user_id), None)
        if member is None:
            raise NotFoundError("Member not found.")
        if member.role == ProjectRole.OWNER:
            raise BadRequestError("The project owner cannot be removed.")

        project.members.remove(member)  # delete-orphan removes the row
        self._db.commit()

    # --- helpers -------------------------------------------------------------

    def _get_visible(
        self, user: User, project_id: uuid.UUID
    ) -> tuple[Project, ProjectRole | None]:
        """Return the project and the caller's project role.

        Non-members get 404 (not 403) so the project's existence is not revealed.
        Admins can see every project.
        """
        project = self._projects.get_by_id(project_id)
        if project is None:
            raise NotFoundError(PROJECT_NOT_FOUND)

        role = next((m.role for m in project.members if m.user_id == user.id), None)
        if role is None and user.role != UserRole.ADMIN:
            raise NotFoundError(PROJECT_NOT_FOUND)
        return project, role

    @staticmethod
    def _require_manage(user: User, role: ProjectRole | None) -> None:
        if user.role != UserRole.ADMIN and role != ProjectRole.OWNER:
            raise PermissionDeniedError("Only the project owner can do this.")

    def _reload(self, project_id: uuid.UUID) -> Project:
        project = self._projects.get_by_id(project_id)
        if project is None:  # cannot happen right after a successful commit
            raise NotFoundError(PROJECT_NOT_FOUND)
        return project
