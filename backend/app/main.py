from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from app.api.router import api_router
from app.core.error_handlers import (
    app_error_handler,
    request_validation_handler,
    unhandled_error_handler,
)
from app.core.exceptions import AppError

app = FastAPI(title="Recipe Vault", version="0.1.0")

app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(RequestValidationError, request_validation_handler)
app.add_exception_handler(Exception, unhandled_error_handler)

app.include_router(api_router)


@app.get("/health")
def health():
    return {"status": "ok"}
