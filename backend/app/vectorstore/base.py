"""Protocol (interface) for vector store providers."""
from typing import Any, Optional, Protocol


class VectorStoreProvider(Protocol):
    def upsert(self, point_id: str, vector: list[float], payload: dict[str, Any]) -> None:
        """Insert or overwrite a single vector with its payload."""
        ...

    def delete(self, point_id: str) -> None:
        """Remove a vector by its ID."""
        ...

    def search(
        self,
        vector: list[float],
        top_k: int = 10,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        """
        ANN search. Returns a list of payloads (with _score and _id injected)
        ordered by descending similarity.
        """
        ...
