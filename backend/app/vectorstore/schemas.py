"""
Pydantic schema for the Qdrant point payload.

Mirrors the Chunk fields that are relevant at search/retrieval time,
plus recipe-level metadata the chunker doesn't have (owner_id, title, tags).

Chunk (chunker) → embed → RecipePayload (Qdrant payload) + vector → upsert

Fields carried from Chunk:
  recipe_id   — for dedup and mapping results back to Postgres
  chunk_type  — "meta" | "ingredients" | "steps" | "full"

Fields added by the ingestion pipeline:
  owner_id    — filters search results to the requesting user
  title       — for search result cards without a Postgres roundtrip
  description — for search result cards without a Postgres roundtrip
  cuisine, difficulty, tag_names — for filtering and display
"""
from typing import Literal, Optional

from pydantic import BaseModel


class RecipePayload(BaseModel):
    # From Chunk
    recipe_id: str
    chunk_type: Literal["meta", "ingredients", "steps", "full"]

    # Added by pipeline
    owner_id: str
    title: str
    description: Optional[str] = None
    cuisine: Optional[str] = None
    difficulty: Optional[str] = None
    tag_names: list[str] = []
