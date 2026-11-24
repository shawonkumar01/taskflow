from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user import UserUpdate


class UserService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def update_profile(self, user: User, data: UserUpdate) -> User:
        changes = data.model_dump(exclude_unset=True, exclude_none=True)
        for field, value in changes.items():
            setattr(user, field, value)
        self._db.commit()
        return user
