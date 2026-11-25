import uuid
from dataclasses import dataclass

from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.models.project import Project
from app.models.project_member import ProjectRole
from app.models.user import User, UserRole
from app.repositories.project import ProjectRepository


@dataclass(frozen=True)
class ProjectAccess:
    """What the acting user may do inside one project."""

    project: Project
    user: User
    role: ProjectRole | None  # None for an admin who is not a member

    @property
    def is_admin(self) -> bool:
        return self.user.role == UserRole.ADMIN

    @property
    def can_manage(self) -> bool:
        return self.is_admin or self.role == ProjectRole.OWNER

    def has_member(self, user_id: uuid.UUID) -> bool:
        return any(member.user_id == user_id for member in self.project.members)

    def require_manage(self) -> None:
        if not self.can_manage:
            raise PermissionDeniedError("Only the project owner can do this.")


def load_project_access(
    projects: ProjectRepository,
    user: User,
    project_id: uuid.UUID,
    not_found_message: str = "Project not found.",
) -> ProjectAccess:
    """Load a project and the caller's access to it.

    Non-members get 404 (not 403) so the existence of the project is not revealed.
    Admins can access every project.
    """
    project = projects.get_by_id(project_id)
    if project is None:
        raise NotFoundError(not_found_message)

    role = next((m.role for m in project.members if m.user_id == user.id), None)
    if role is None and user.role != UserRole.ADMIN:
        raise NotFoundError(not_found_message)
    return ProjectAccess(project=project, user=user, role=role)
