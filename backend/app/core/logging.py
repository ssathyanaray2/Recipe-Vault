"""
Structured logging for Recipe Vault.

Two modes controlled by LOG_FORMAT in settings:
  console — colored, human-readable output for local development
  json    — machine-readable output for production and eval runs

Usage in any module:
    import structlog
    logger = structlog.get_logger(__name__)

    # Plain log
    logger.info("recipe.created", recipe_id=str(id), title=title)

    # Timed block — logs elapsed_ms automatically
    from app.core.logging import timed
    with timed(logger, "embed_chunks", recipe_id=str(id), chunk_count=len(chunks)):
        vectors = provider.embed(texts)

    # Bind context once, reuse across a request
    log = logger.bind(recipe_id=str(id), user_id=str(uid))
    log.info("step.start")
    ...
    log.info("step.done")
"""
import logging
import sys
import time
from contextlib import contextmanager
from typing import Any, Generator

import structlog


def setup_logging(log_level: str = "INFO", log_format: str = "console") -> None:
    """
    Configure structlog + stdlib logging.
    Call once at application startup before the first log line is emitted.
    stdlib loggers (logging.getLogger) are routed through structlog automatically.
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    # Processors applied to every log record regardless of format
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if log_format == "json":
        # Flat JSON — easy to query with jq or ship to Datadog / CloudWatch
        renderer: Any = structlog.processors.JSONRenderer()
    else:
        # Colored, aligned output — fast to read during development
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        # Applied to stdlib log records before structlog takes over
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # Suppress noisy third-party libraries
    for noisy in ("httpx", "httpcore", "hpack", "uvicorn.access"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


@contextmanager
def timed(
    logger: Any,
    operation: str,
    **ctx: Any,
) -> Generator[Any, None, None]:
    """
    Context manager that logs start, completion, and elapsed_ms for any operation.
    On exception, logs the error with elapsed time and re-raises.

    Args:
        logger:    structlog logger (from structlog.get_logger())
        operation: dot-namespaced name, e.g. "embed_chunks", "qdrant.upsert"
        **ctx:     extra fields bound to every log line inside the block
                   e.g. recipe_id=str(id), chunk_count=5

    Example (ingestion pipeline):
        with timed(logger, "embed_chunks", recipe_id=str(recipe_id), chunk_count=len(chunks)):
            vectors = provider.embed(texts)
        # → logs: embed_chunks.done  elapsed_ms=312.4  recipe_id=...  chunk_count=5

    Example (retrieval — future):
        with timed(logger, "qdrant.search", query=query, top_k=top_k):
            results = vectorstore.search(vector, top_k=top_k)
        # → logs: qdrant.search.done  elapsed_ms=28.1  query=...  top_k=20
    """
    bound = logger.bind(**ctx) if ctx else logger
    bound.debug(f"{operation}.start")
    t0 = time.perf_counter()
    try:
        yield bound
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        bound.info(f"{operation}.done", elapsed_ms=elapsed_ms)
    except Exception:
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        bound.error(f"{operation}.error", elapsed_ms=elapsed_ms, exc_info=True)
        raise
