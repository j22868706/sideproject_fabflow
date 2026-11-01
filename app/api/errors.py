"""JSON error responses without echoing invalid request values."""

import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ErrorResponse(BaseModel):
    detail: str


class ValidationIssue(BaseModel):
    loc: list[str | int]
    msg: str
    type: str


class ValidationErrorResponse(BaseModel):
    detail: list[ValidationIssue]


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Return field paths and validation reasons as JSON-safe 422 details."""
    # Pydantic input/ctx can contain NaN, infinity, or exception objects that
    # cannot be serialized as JSON. Return only the actionable error metadata.
    response = ValidationErrorResponse(
        detail=[
            ValidationIssue(loc=list(error["loc"]), msg=error["msg"], type=error["type"])
            for error in exc.errors()
        ]
    )
    return JSONResponse(status_code=422, content=response.model_dump())


async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Log the diagnostic exception and return a generic JSON 500 response."""
    logger.error("Unhandled API error on %s", request.url.path, exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


async def storage_unavailable_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return a generic 503 response when result storage is unavailable."""
    logger.error("Result storage unavailable on %s", request.url.path)
    return JSONResponse(
        status_code=503,
        content={"detail": "Result storage is unavailable"},
    )
