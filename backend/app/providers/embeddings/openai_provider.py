"""OpenAI embedding provider."""
import logging
from typing import Literal

from openai import OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

# OpenAI does not distinguish document vs query at the API level —
# both use the same endpoint. input_type is accepted but ignored.


class OpenAIEmbeddingProvider:
    def __init__(self) -> None:
        self._client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self._model = settings.OPENAI_EMBEDDING_MODEL

    def embed(
        self,
        texts: list[str],
        input_type: Literal["document", "query"] = "document",
    ) -> list[list[float]]:
        if not texts:
            return []
        response = self._client.embeddings.create(input=texts, model=self._model)
        logger.debug("Embedded %d texts with %s", len(texts), self._model)
        return [item.embedding for item in response.data]
