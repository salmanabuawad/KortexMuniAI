"""Uniform error handling.

Users never see raw stack traces (spec §52). They get a friendly message plus a
reference ID; administrators get the full detail in the logs.
"""

from __future__ import annotations

import uuid

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger

logger = get_logger("muniai.errors")


class MuniAIError(Exception):
    """Base class for expected, user-safe application errors."""

    def __init__(self, message: str, *, status_code: int = 400, code: str = "error"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


def _payload(message: str, code: str, ref: str | None = None) -> dict:
    body = {"error": {"code": code, "message": message}}
    if ref:
        body["error"]["reference_id"] = ref
    return body


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(MuniAIError)
    async def _muniai(_: Request, exc: MuniAIError) -> JSONResponse:
        return JSONResponse(_payload(exc.message, exc.code), status_code=exc.status_code)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            _payload(str(exc.detail), "http_error"),
            status_code=exc.status_code,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            {"error": {"code": "validation_error", "message": "Invalid request.",
                       "details": jsonable_encoder(exc.errors())}},
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        ref = uuid.uuid4().hex[:12]
        logger.exception("Unhandled error [ref=%s]: %s", ref, exc)
        return JSONResponse(
            _payload(
                "An unexpected error occurred. Please contact an administrator.",
                "internal_error",
                ref,
            ),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
