"""
Ingestion pipeline — orchestrates the full flow for one recipe:
  chunk → embed (batch) → delete old Qdrant points → upsert new points → update marker row

Idempotent: computes a content hash from all chunk texts. If the hash matches
the stored marker, the recipe hasn't changed and the run is skipped.
"""
import hashlib
import uuid

import structlog
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import timed
from app.ingestion.chunking.base import Chunk
from app.ingestion.chunking.factory import get_chunker
from app.models.embedding import EmbeddingStatus, RecipeEmbedding
from app.models.ingredient import RecipeIngredient
from app.models.recipe import Recipe, RecipeStep
from app.models.tag import RecipeTag, Tag
from app.providers.embeddings.factory import get_embedding_provider
from app.vectorstore.qdrant import QdrantVectorStore
from app.vectorstore.schemas import RecipePayload

logger = structlog.get_logger(__name__)


def _content_hash(chunks: list[Chunk]) -> str:
    """MD5 of all chunk texts joined — fast fingerprint for drift detection."""
    combined = "\n---\n".join(c.text for c in chunks)
    return hashlib.md5(combined.encode()).hexdigest()


def _active_model_name() -> str:
    """Human-readable identifier for the currently configured embedding model."""
    provider = settings.EMBEDDING_PROVIDER.lower()
    model_map = {
        "voyage": settings.VOYAGE_EMBEDDING_MODEL,
        "openai": settings.OPENAI_EMBEDDING_MODEL,
        "huggingface": settings.HUGGINGFACE_EMBEDDING_MODEL,
    }
    model = model_map.get(provider, "unknown")
    return f"{provider}/{model}"


def _fetch_related(db: Session, recipe_id: uuid.UUID):
    steps = (
        db.query(RecipeStep)
        .filter_by(recipe_id=recipe_id)
        .order_by(RecipeStep.step_number)
        .all()
    )
    ingredients = (
        db.query(RecipeIngredient)
        .filter_by(recipe_id=recipe_id)
        .order_by(RecipeIngredient.position)
        .all()
    )
    tags = (
        db.query(Tag)
        .join(RecipeTag, Tag.id == RecipeTag.tag_id)
        .filter(RecipeTag.recipe_id == recipe_id)
        .all()
    )
    return steps, ingredients, tags


def ingest_recipe(db: Session, recipe_id: uuid.UUID) -> None:
    """
    Full ingestion for one recipe. Safe to call multiple times — skips
    re-embedding when content has not changed since the last run.
    """
    log = logger.bind(recipe_id=str(recipe_id))

    recipe = db.get(Recipe, recipe_id)
    if not recipe:
        log.warning("ingest_recipe.skipped", reason="recipe_not_found")
        return

    log = log.bind(title=recipe.title)

    # --- Chunk ---
    with timed(log, "chunking"):
        steps, ingredients, tags = _fetch_related(db, recipe_id)
        chunker = get_chunker()
        chunks = chunker.chunk(recipe, steps, ingredients, tags)

    # --- Idempotency check ---
    content_hash = _content_hash(chunks)
    marker = db.get(RecipeEmbedding, recipe_id)

    if marker and marker.embedding_text == content_hash:
        log.info("ingest_recipe.skipped", reason="content_unchanged")
        return

    # --- Embed all chunks in one batch call ---
    with timed(log, "embedding", chunk_count=len(chunks), model=_active_model_name()):
        provider = get_embedding_provider()
        texts = [c.text for c in chunks]
        vectors = provider.embed(texts, input_type="document")

    # --- Delete stale Qdrant chunks before upserting new ones ---
    vectorstore = QdrantVectorStore()
    if marker:
        with timed(log, "qdrant.delete_stale"):
            vectorstore.delete_by_recipe(str(recipe_id))

    # --- Build payload and upsert each chunk ---
    base_payload = dict(
        owner_id=str(recipe.owner_id),
        title=recipe.title,
        description=recipe.description,
        cuisine=recipe.cuisine,
        difficulty=recipe.difficulty.value if recipe.difficulty else None,
        tag_names=[t.name for t in tags],
    )

    with timed(log, "qdrant.upsert", chunk_count=len(chunks)):
        for chunk, vector in zip(chunks, vectors):
            payload = RecipePayload(
                recipe_id=chunk.recipe_id,
                chunk_type=chunk.chunk_type,
                **base_payload,
            )
            vectorstore.upsert(chunk.point_id, vector, payload.model_dump())

    # --- Write / update marker row ---
    model_name = _active_model_name()
    if marker:
        marker.embedding_text = content_hash
        marker.model_name = model_name
        marker.status = EmbeddingStatus.EMBEDDED
    else:
        db.add(RecipeEmbedding(
            recipe_id=recipe_id,
            model_name=model_name,
            embedding_text=content_hash,
            status=EmbeddingStatus.EMBEDDED,
        ))

    db.commit()
    log.info("ingest_recipe.done", chunk_count=len(chunks), model=model_name)
