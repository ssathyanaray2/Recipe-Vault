"""
HuggingFace embedding provider — runs locally via sentence-transformers.
No API key required. Useful for local dev and cost-free evaluation.

Note: first run downloads the model (~100MB for bge-small). Subsequent
runs load from cache. Set HUGGINGFACE_EMBEDDING_MODEL in .env to switch models.
"""
import logging
from typing import Literal

from app.core.config import settings

logger = logging.getLogger(__name__)


class HuggingFaceEmbeddingProvider:
    def __init__(self) -> None:
        # Lazy import — sentence-transformers is heavy, only load when needed
        from sentence_transformers import SentenceTransformer
        self._model_name = settings.HUGGINGFACE_EMBEDDING_MODEL
        self._model = SentenceTransformer(self._model_name)
        logger.info("Loaded HuggingFace model: %s", self._model_name)

    def embed(
        self,
        texts: list[str],
        input_type: Literal["document", "query"] = "document",
    ) -> list[list[float]]:
        if not texts:
            return []
        # bge models use a prefix for query vs document
        if input_type == "query":
            texts = [f"Represent this sentence for searching relevant passages: {t}" for t in texts]
        embeddings = self._model.encode(texts, normalize_embeddings=True)
        logger.debug("Embedded %d texts with %s", len(texts), self._model_name)
        return embeddings.tolist()
