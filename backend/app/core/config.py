from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    DATABASE_URL: str

    # Auth
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Anthropic
    ANTHROPIC_API_KEY: str = ""

    # Embedding provider
    # Options: "voyage" | "openai" | "huggingface"
    EMBEDDING_PROVIDER: str = "voyage"

    # Voyage
    VOYAGE_API_KEY: str = ""
    VOYAGE_EMBEDDING_MODEL: str = "voyage-3"

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # HuggingFace (local, no API key needed)
    HUGGINGFACE_EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"

    # Reranker
    RERANKER_PROVIDER: str = "cohere"
    COHERE_API_KEY: str = ""

    # Qdrant
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION_NAME: str = "recipes"

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # Chunking
    # Options: "single" (one vector per recipe) | "structured" (meta + ingredients + steps chunks)
    CHUNKING_STRATEGY: str = "structured"
    CHUNK_MAX_TOKENS: int = 500  # max tokens per chunk before splitting (~2000 chars)


settings = Settings()
