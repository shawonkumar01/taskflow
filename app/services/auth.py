import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repositories.refresh_token import RefreshTokenRepository
from app.repositories.user import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest, TokenPair

INVALID_CREDENTIALS = "Invalid email or password."
INVALID_REFRESH_TOKEN = "Invalid or expired refresh token."


class AuthService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._users = UserRepository(db)
        self._tokens = RefreshTokenRepository(db)

    def register(self, data: RegisterRequest) -> User:
        if self._users.get_by_email(data.email) is not None:
            raise ConflictError("Email is already registered.")

        user = User(
            email=data.email,
            full_name=data.full_name,
            hashed_password=hash_password(data.password),
        )
        try:
            self._users.add(user)
            self._db.commit()
        except IntegrityError:  # lost a race with a concurrent registration
            self._db.rollback()
            raise ConflictError("Email is already registered.") from None
        return user

    def login(self, data: LoginRequest) -> TokenPair:
        user = self._users.get_by_email(data.email)
        # Always verify one hash so timing does not reveal whether the email exists.
        stored_hash = user.hashed_password if user else DUMMY_PASSWORD_HASH
        password_ok = verify_password(data.password, stored_hash)

        if user is None or not password_ok or not user.is_active:
            raise UnauthorizedError(INVALID_CREDENTIALS)

        tokens = self._issue_tokens(user, family_id=uuid.uuid4())
        self._db.commit()
        return tokens

    def refresh(self, raw_token: str) -> TokenPair:
        now = datetime.now(UTC)
        stored = self._tokens.get_by_hash(hash_token(raw_token))
        if stored is None:
            raise UnauthorizedError(INVALID_REFRESH_TOKEN)

        if stored.revoked_at is not None:
            # A used token came back: assume theft and kill the whole family.
            self._tokens.revoke_family(stored.family_id, now)
            self._db.commit()
            raise UnauthorizedError(INVALID_REFRESH_TOKEN)

        if stored.expires_at <= now:
            raise UnauthorizedError(INVALID_REFRESH_TOKEN)

        user = self._users.get_by_id(stored.user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError(INVALID_REFRESH_TOKEN)

        stored.revoked_at = now  # rotation: each refresh token works exactly once
        tokens = self._issue_tokens(user, family_id=stored.family_id)
        self._db.commit()
        return tokens

    def logout(self, raw_token: str) -> None:
        stored = self._tokens.get_by_hash(hash_token(raw_token))
        if stored is not None:
            self._tokens.revoke_family(stored.family_id, datetime.now(UTC))
            self._db.commit()

    def _issue_tokens(self, user: User, family_id: uuid.UUID) -> TokenPair:
        settings = get_settings()
        raw_refresh = generate_refresh_token()
        self._tokens.add(
            RefreshToken(
                user_id=user.id,
                token_hash=hash_token(raw_refresh),
                family_id=family_id,
                expires_at=datetime.now(UTC)
                + timedelta(days=settings.refresh_token_expire_days),
            )
        )
        return TokenPair(
            access_token=create_access_token(user.id, user.role.value),
            refresh_token=raw_refresh,
            expires_in=settings.access_token_expire_minutes * 60,
        )
