from fastapi import FastAPI

from app.api.error_handlers import register_exception_handlers
from app.api.v1.endpoints import health
from app.api.v1.router import api_router
from app.core.config import Environment, get_settings


def create_app() -> FastAPI:
    is_production = get_settings().environment == Environment.PRODUCTION

    app = FastAPI(
        title="TaskFlow API",
        version="0.1.0",
        docs_url=None if is_production else "/docs",
        redoc_url=None if is_production else "/redoc",
        openapi_url=None if is_production else "/openapi.json",
    )
    register_exception_handlers(app)
    app.include_router(health.router)  # probes live at the root, unversioned
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
