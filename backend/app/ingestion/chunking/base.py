"""
Shared types for all chunking strategies.
"""
from dataclasses import dataclass, field
from typing import Protocol

from app.models.ingredient import RecipeIngredient
from app.models.recipe import Recipe, RecipeStep
from app.models.tag import Tag


@dataclass
class Chunk:
    """
    A single unit ready to be embedded and upserted into Qdrant.

    point_id   — unique Qdrant ID: "{recipe_id}:meta", "{recipe_id}:ingredients:0", etc.
    text       — the text that gets sent to the embedding model
    chunk_type — "meta" | "ingredients" | "steps" | "full"
    recipe_id  — stored in Qdrant payload for dedup and owner filtering at search time
    metadata   — any extra fields to store in the Qdrant payload
    """
    point_id: str
    text: str
    chunk_type: str
    recipe_id: str
    metadata: dict = field(default_factory=dict)


class RecipeChunker(Protocol):
    """
    Interface all chunking strategies must satisfy.
    The pipeline calls chunk() and gets back a list of Chunk objects —
    one per vector to be upserted into Qdrant.
    """
    def chunk(
        self,
        recipe: Recipe,
        steps: list[RecipeStep],
        ingredients: list[RecipeIngredient],
        tags: list[Tag],
    ) -> list[Chunk]:
        ...
