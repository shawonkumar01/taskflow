from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.error_handlers import register_exception_handlers
from app.api.v1.endpoints import health
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.middleware import (
    BodySizeLimitMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)
from app.core.rate_limit import default_rate_limit


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level, json_logs=settings.is_production)

    app = FastAPI(
        title="TaskFlow API",
        version="0.1.0",
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None if settings.is_production else "/redoc",
        openapi_url=None if settings.is_production else "/openapi.json",
    )
    register_exception_handlers(app)
    app.include_router(health.router)  # probes: unversioned and never rate limited
    app.include_router(
        api_router, prefix="/api/v1", dependencies=[Depends(default_rate_limit)]
    )

    # Added innermost first: the last one added runs first on a request.
    app.add_middleware(
        BodySizeLimitMiddleware, max_bytes=settings.max_request_body_bytes
    )
    if settings.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_credentials=False,  # tokens travel in headers, not cookies
            allow_methods=["GET", "POST", "PATCH", "DELETE"],
            allow_headers=["Authorization", "Content-Type"],
        )
    app.add_middleware(SecurityHeadersMiddleware, hsts=settings.is_production)
    app.add_middleware(RequestContextMiddleware)
    return app


app = create_app()
