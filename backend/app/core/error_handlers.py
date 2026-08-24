"""
Global exception handlers — registered on the FastAPI app in main.py.
Every error response uses the same shape: {"error": "<CODE>", "message": "<text>"}
Validation errors add a "detail" list for field-level information.
"""
import logging

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    AppError,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)

logger = logging.getLogger(__name__)

# Map domain exception → (HTTP status, error code string)
_STATUS_MAP: dict[type[AppError], tuple[int, str]] = {
    NotFoundError: (status.HTTP_404_NOT_FOUND, "NOT_FOUND"),
    ConflictError: (status.HTTP_409_CONFLICT, "CONFLICT"),
    AuthenticationError: (status.HTTP_401_UNAUTHORIZED, "UNAUTHORIZED"),
    AuthorizationError: (status.HTTP_403_FORBIDDEN, "FORBIDDEN"),
    ValidationError: (status.HTTP_422_UNPROCESSABLE_CONTENT, "VALIDATION_ERROR"),
}


def _error_body(error: str, message: str, detail=None) -> dict:
    body = {"error": error, "message": message}
    if detail is not None:
        body["detail"] = detail
    return body


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    http_status, error_code = _STATUS_MAP.get(type(exc), (status.HTTP_500_INTERNAL_SERVER_ERROR, "INTERNAL_ERROR"))
    return JSONResponse(status_code=http_status, content=_error_body(error_code, exc.message))


async def request_validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Pydantic / FastAPI schema validation errors — 422 with field-level detail."""
    errors = [
        {"field": ".".join(str(loc) for loc in e["loc"][1:]), "message": e["msg"]}
        for e in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=_error_body("VALIDATION_ERROR", "Request validation failed", detail=errors),
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_error_body("INTERNAL_ERROR", "An unexpected error occurred"),
    )
