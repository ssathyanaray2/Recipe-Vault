"""
Celery tasks for recipe ingestion.
Each task opens its own DB session — Celery workers are separate processes
from the FastAPI app and cannot share the request-scoped session.
"""
import uuid

import structlog

from app.core.celery import celery_app
from app.core.config import settings
from app.core.logging import timed
from app.db.session import SessionLocal
from app.ingestion.pipeline import ingest_recipe as run_pipeline

logger = structlog.get_logger(__name__)


class _IngestRecipeTask(celery_app.Task):
    """
    Base class for ingest_recipe so we can define on_failure as a real method.
    on_failure is called once — after all retries are exhausted.
    """
    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        recipe_id = args[0] if args else kwargs.get("recipe_id")
        if not recipe_id:
            return
        db = SessionLocal()
        try:
            from app.models.embedding import EmbeddingStatus, RecipeEmbedding
            marker = db.get(RecipeEmbedding, uuid.UUID(recipe_id))
            if marker:
                marker.status = EmbeddingStatus.FAILED
                db.commit()
                logger.error(
                    "Ingestion permanently failed for recipe %s — marked FAILED", recipe_id
                )
        except Exception:
            logger.error("on_failure.error", recipe_id=recipe_id, exc_info=True)
        finally:
            db.close()


@celery_app.task(
    bind=True,
    base=_IngestRecipeTask,
    max_retries=settings.INGESTION_MAX_RETRIES,
    default_retry_delay=settings.INGESTION_RETRY_DELAY,
    name="ingestion.ingest_recipe",
)
def ingest_recipe(self, recipe_id: str) -> None:
    """
    Trigger the full ingestion pipeline for a single recipe.
    Retried up to 3 times on failure with a 60-second delay.
    On permanent failure (all retries exhausted), on_failure marks the
    marker row FAILED so reindex_qdrant.py can replay it.

    Called from recipes/service.py after create or update:
        ingest_recipe.delay(str(recipe_id))
    """
    log = logger.bind(recipe_id=recipe_id, attempt=self.request.retries + 1)
    db = SessionLocal()
    try:
        with timed(log, "ingest_recipe"):
            run_pipeline(db, uuid.UUID(recipe_id))
    except Exception as exc:
        log.warning("ingest_recipe.retry", exc=str(exc))
        raise self.retry(exc=exc)
    finally:
        db.close()
