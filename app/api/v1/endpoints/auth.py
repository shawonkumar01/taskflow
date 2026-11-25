from fastapi import APIRouter, Depends, status

from app.api.deps import AuthServiceDep
from app.core.rate_limit import auth_rate_limit
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenPair
from app.schemas.user import UserRead

router = APIRouter(prefix="/auth", tags=["auth"])

strict_limit = [Depends(auth_rate_limit)]


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=strict_limit,
)
def register(data: RegisterRequest, service: AuthServiceDep) -> User:
    return service.register(data)


@router.post("/login", response_model=TokenPair, dependencies=strict_limit)
def login(data: LoginRequest, service: AuthServiceDep) -> TokenPair:
    return service.login(data)


@router.post("/refresh", response_model=TokenPair, dependencies=strict_limit)
def refresh(data: RefreshRequest, service: AuthServiceDep) -> TokenPair:
    return service.refresh(data.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(data: RefreshRequest, service: AuthServiceDep) -> None:
    service.logout(data.refresh_token)
