"""Protocol (interface) for embedding providers."""
from typing import Literal, Protocol


class EmbeddingProvider(Protocol):
    def embed(
        self,
        texts: list[str],
        input_type: Literal["document", "query"] = "document",
    ) -> list[list[float]]:
        """
        Embed a batch of texts.
        input_type="document" for ingestion, "query" for search.
        Returns one vector per input text.
        """
        ...
