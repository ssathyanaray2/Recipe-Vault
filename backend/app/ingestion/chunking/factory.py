"""
Returns the configured chunker based on CHUNKING_STRATEGY in settings.

Adding a new strategy (e.g. LangChain):
  1. Create a new class implementing the RecipeChunker Protocol
  2. Add a new branch here
  3. Set CHUNKING_STRATEGY=langchain in .env
"""
from app.core.config import settings
from app.ingestion.chunking.base import RecipeChunker


def get_chunker() -> RecipeChunker:
    strategy = settings.CHUNKING_STRATEGY.lower()

    if strategy == "structured":
        from app.ingestion.chunking.structured_chunker import StructuredRecipeChunker
        return StructuredRecipeChunker()

    if strategy == "single":
        from app.ingestion.chunking.single_chunker import SingleRecipeChunker
        return SingleRecipeChunker()

    raise ValueError(
        f"Unknown CHUNKING_STRATEGY '{strategy}'. "
        "Valid options: 'structured', 'single'."
    )
