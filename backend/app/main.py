from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from sqlalchemy import text

from app.api.router import api_router
from app.core.config import settings
from app.core.error_handlers import (
    app_error_handler,
    request_validation_handler,
    unhandled_error_handler,
)
from app.core.exceptions import AppError
from app.core.logging import setup_logging
from app.db.session import SessionLocal

# Configure logging before anything else emits a log line
setup_logging(log_level=settings.LOG_LEVEL, log_format=settings.LOG_FORMAT)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ------------------------------------------------------------------
    # Startup — runs before the first request is served
    # ------------------------------------------------------------------
    logger.info("Starting up Recipe Vault...")

    # Verify Postgres is reachable
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        logger.info("Postgres connection OK")
    except Exception as e:
        logger.critical("Postgres unreachable at startup: %s", e)
        raise

    # Verify Qdrant is reachable and collection exists
    # (skipped if Qdrant is not yet configured — ingestion phase)
    try:
        from app.vectorstore.qdrant import QdrantVectorStore
        QdrantVectorStore()
        logger.info("Qdrant connection OK")
    except Exception as e:
        logger.warning("Qdrant not reachable at startup: %s — vector search unavailable", e)

    logger.info("Recipe Vault is ready")

    yield

    # ------------------------------------------------------------------
    # Shutdown — runs after the last request, before process exits
    # ------------------------------------------------------------------
    logger.info("Shutting down Recipe Vault...")


app = FastAPI(title="Recipe Vault", version="0.1.0", lifespan=lifespan)

app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(RequestValidationError, request_validation_handler)
app.add_exception_handler(Exception, unhandled_error_handler)

app.include_router(api_router)


@app.get("/health")
def health():
    return {"status": "ok"}
