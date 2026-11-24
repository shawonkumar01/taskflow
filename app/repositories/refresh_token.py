import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.refresh_token import RefreshToken


class RefreshTokenRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def add(self, token: RefreshToken) -> RefreshToken:
        self._db.add(token)
        self._db.flush()
        return token

    def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        """Row-locked read so two concurrent refreshes cannot both succeed."""
        stmt = (
            select(RefreshToken)
            .where(RefreshToken.token_hash == token_hash)
            .with_for_update()
        )
        return self._db.execute(stmt).scalar_one_or_none()

    def revoke_family(self, family_id: uuid.UUID, revoked_at: datetime) -> None:
        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.family_id == family_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=revoked_at)
        )
        self._db.execute(stmt)
