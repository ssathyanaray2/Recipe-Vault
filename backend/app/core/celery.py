"""
Celery application instance.
Import this module to access the Celery app — do not create a second instance elsewhere.

Start the worker:
    celery -A app.core.celery worker --loglevel=info
"""
from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "recipe_vault",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.ingestion.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)
