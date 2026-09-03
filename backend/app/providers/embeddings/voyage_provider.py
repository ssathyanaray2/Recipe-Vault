"""Voyage AI embedding provider."""
from typing import Literal

import structlog
import voyageai

from app.core.config import settings

logger = structlog.get_logger(__name__)


class VoyageEmbeddingProvider:
    def __init__(self) -> None:
        self._client = voyageai.Client(api_key=settings.VOYAGE_API_KEY)
        self._model = settings.VOYAGE_EMBEDDING_MODEL

    def embed(
        self,
        texts: list[str],
        input_type: Literal["document", "query"] = "document",
    ) -> list[list[float]]:
        if not texts:
            return []
        result = self._client.embed(texts, model=self._model, input_type=input_type)
        logger.debug("embed.done", count=len(texts), model=self._model)
        return result.embeddings
