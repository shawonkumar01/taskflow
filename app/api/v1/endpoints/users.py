from fastapi import APIRouter

from app.api.deps import CurrentUser, UserServiceDep
from app.models.user import User
from app.schemas.user import UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
def read_me(current_user: CurrentUser) -> User:
    return current_user


@router.patch("/me", response_model=UserRead)
def update_me(
    data: UserUpdate, current_user: CurrentUser, service: UserServiceDep
) -> User:
    return service.update_profile(current_user, data)
