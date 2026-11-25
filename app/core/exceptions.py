from typing import Any


class AppError(Exception):
    """Base class for domain errors. Mapped to HTTP responses in api/error_handlers.py."""

    code = "app_error"
    default_message = "An error occurred."

    def __init__(self, message: str | None = None, details: Any = None) -> None:
        self.message = message or self.default_message
        self.details = details
        super().__init__(self.message)


class BadRequestError(AppError):
    code = "bad_request"
    default_message = "Bad request."


class UnauthorizedError(AppError):
    code = "unauthorized"
    default_message = "Authentication required."


class PermissionDeniedError(AppError):
    code = "permission_denied"
    default_message = "You do not have permission to do this."


class NotFoundError(AppError):
    code = "not_found"
    default_message = "Resource not found."


class ConflictError(AppError):
    code = "conflict"
    default_message = "Resource already exists."


class RateLimitedError(AppError):
    code = "rate_limited"
    default_message = "Too many requests. Please try again later."

    def __init__(self, retry_after: int | None = None) -> None:
        super().__init__()
        self.retry_after = retry_after
