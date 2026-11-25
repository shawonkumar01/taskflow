import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import (
    AppError,
    BadRequestError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitedError,
    UnauthorizedError,
)
from app.core.logging import request_id_ctx

logger = logging.getLogger(__name__)

STATUS_BY_ERROR: dict[type[AppError], int] = {
    BadRequestError: 400,
    UnauthorizedError: 401,
    PermissionDeniedError: 403,
    NotFoundError: 404,
    ConflictError: 409,
    RateLimitedError: 429,
}


def _body(code: str, message: str, details: Any = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details}}


async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    status_code = STATUS_BY_ERROR.get(type(exc), 400)
    headers: dict[str, str] = {}
    if status_code == 401:
        headers["WWW-Authenticate"] = "Bearer"
    if isinstance(exc, RateLimitedError) and exc.retry_after:
        headers["Retry-After"] = str(exc.retry_after)
    return JSONResponse(
        status_code=status_code,
        content=_body(exc.code, exc.message, exc.details),
        headers=headers or None,
    )


async def handle_http_exception(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=_body("http_error", str(exc.detail)),
        headers=exc.headers,
    )


async def handle_validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    details = [
        {"field": ".".join(str(part) for part in err["loc"][1:]), "message": err["msg"]}
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=_body("validation_error", "Request validation failed.", details),
    )


async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    request_id = request_id_ctx.get()
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content=_body(
            "internal_error",
            "An unexpected error occurred.",
            {"request_id": request_id},
        ),
        headers={"X-Request-ID": request_id},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, handle_app_error)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, handle_http_exception)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, handle_validation_error)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, handle_unexpected_error)
