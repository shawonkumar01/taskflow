import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings
from app.core.exceptions import UnauthorizedError

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_TYPE = "access"

_password_hasher = PasswordHash.recommended()  # Argon2id


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return _password_hasher.verify(password, hashed_password)


# Verified against when an email is unknown, so login timing does not reveal it.
DUMMY_PASSWORD_HASH = hash_password("timing-equalization-placeholder")


def create_access_token(user_id: uuid.UUID, role: str) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "type": ACCESS_TOKEN_TYPE,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            get_settings().secret_key,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("Invalid or expired token.") from exc
    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise UnauthorizedError("Invalid or expired token.")
    return payload


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    """Refresh tokens are stored only as SHA-256 hashes."""
    return hashlib.sha256(token.encode()).hexdigest()
