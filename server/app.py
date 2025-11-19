"""FastAPI application factory."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from server.config import settings
from server.routes import health

__all__ = ["app", "create_app"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and teardown resources."""
    # Reserved for future startup/shutdown logic.
    yield


def create_app() -> FastAPI:
    """Build and configure the FastAPI application instance."""
    application = FastAPI(
        title=settings.app_name,
        version=settings.version,
        debug=settings.debug,
        lifespan=lifespan,
    )
    application.include_router(health.router)
    return application


app = create_app()
