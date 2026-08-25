"""
Returns the configured embedding provider based on EMBEDDING_PROVIDER in settings.

Adding a new provider:
  1. Create a class implementing the EmbeddingProvider Protocol
  2. Add a branch here
  3. Set EMBEDDING_PROVIDER=<name> in .env
"""
from app.core.config import settings
from app.providers.embeddings.base import EmbeddingProvider


def get_embedding_provider() -> EmbeddingProvider:
    provider = settings.EMBEDDING_PROVIDER.lower()

    if provider == "voyage":
        from app.providers.embeddings.voyage_provider import VoyageEmbeddingProvider
        return VoyageEmbeddingProvider()

    if provider == "openai":
        from app.providers.embeddings.openai_provider import OpenAIEmbeddingProvider
        return OpenAIEmbeddingProvider()

    if provider == "huggingface":
        from app.providers.embeddings.huggingface_provider import HuggingFaceEmbeddingProvider
        return HuggingFaceEmbeddingProvider()

    raise ValueError(
        f"Unknown EMBEDDING_PROVIDER '{provider}'. "
        "Valid options: 'voyage', 'openai', 'huggingface'."
    )
