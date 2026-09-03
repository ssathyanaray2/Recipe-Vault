"""
Qdrant vector store implementation.
Owns collection creation and schema — everything else goes through upsert/search/delete.
"""
from typing import Any, Optional

from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    FieldCondition,
    Filter,
    FilterSelector,
    MatchValue,
    PointIdsList,
    PointStruct,
    VectorParams,
)

import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

class QdrantVectorStore:
    def __init__(self) -> None:
        self._client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY or None,
        )
        self._collection = settings.QDRANT_COLLECTION_NAME
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        """
        Create the collection if it does not exist.
        If it already exists, validate that its vector dimension matches the
        active embedding model — a mismatch means the model was switched after
        the collection was created and every upsert will be rejected by Qdrant.
        """
        existing = {c.name for c in self._client.get_collections().collections}
        expected_size = settings.EMBEDDING_VECTOR_SIZE

        if self._collection not in existing:
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(size=expected_size, distance=Distance.COSINE),
            )
            logger.info("Created Qdrant collection '%s' (dim=%d)", self._collection, expected_size)
            return

        info = self._client.get_collection(self._collection)
        actual_size = info.config.params.vectors.size
        if actual_size != expected_size:
            raise RuntimeError(
                f"Qdrant collection '{self._collection}' has dim={actual_size} but the "
                f"active embedding model produces dim={expected_size}. "
                "Run `python scripts/reindex_qdrant.py` after recreating the collection "
                "with the correct dimension, or switch back to the original model."
            )

    def upsert(self, point_id: str, vector: list[float], payload: dict[str, Any]) -> None:
        self._client.upsert(
            collection_name=self._collection,
            points=[PointStruct(id=point_id, vector=vector, payload=payload)],
        )

    def delete(self, point_id: str) -> None:
        """Delete a single point by its ID."""
        self._client.delete(
            collection_name=self._collection,
            points_selector=PointIdsList(points=[point_id]),
        )

    def delete_by_recipe(self, recipe_id: str) -> None:
        """
        Delete ALL chunks belonging to a recipe.
        Used before re-embedding to avoid stale chunks when chunk count changes
        (e.g. a recipe that previously had 2 ingredient chunks now has 3).
        Filters on the recipe_id payload field — not point IDs.
        """
        self._client.delete(
            collection_name=self._collection,
            points_selector=FilterSelector(
                filter=Filter(
                    must=[FieldCondition(key="recipe_id", match=MatchValue(value=recipe_id))]
                )
            ),
        )
        logger.debug("Deleted all Qdrant chunks for recipe %s", recipe_id)

    def search(
        self,
        vector: list[float],
        top_k: int = 10,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        qdrant_filter = None
        if filters:
            qdrant_filter = Filter(
                must=[
                    FieldCondition(key=k, match=MatchValue(value=v))
                    for k, v in filters.items()
                ]
            )

        results = self._client.search(
            collection_name=self._collection,
            query_vector=vector,
            limit=top_k,
            query_filter=qdrant_filter,
            with_payload=True,
        )

        return [
            {**hit.payload, "_score": hit.score, "_id": hit.id}
            for hit in results
        ]
