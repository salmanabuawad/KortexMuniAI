"""MuniAI FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging, get_logger

logger = get_logger("muniai")


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    logger.info("Starting MuniAI %s (env=%s, provider=%s)",
                __version__, settings.env, settings.ai_provider)
    yield
    logger.info("MuniAI shutting down.")


def create_app() -> FastAPI:
    app = FastAPI(
        title="MuniAI API",
        version=__version__,
        docs_url="/api/v1/docs",
        openapi_url="/api/v1/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
