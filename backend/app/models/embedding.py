import enum

from sqlalchemy import Enum as SQLAlchemyEnum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class EmbeddingStatus(str, enum.Enum):
    PENDING = "pending"    # task queued, not yet processed
    EMBEDDED = "embedded"  # successfully embedded and upserted to Qdrant
    FAILED = "failed"      # all retries exhausted — needs manual replay


class RecipeEmbedding(TimestampMixin, Base):
    """
    Marker row — the actual vector lives in Qdrant, keyed by recipe_id.
    Tracks embedding state so failed jobs can be identified and replayed
    via scripts/reindex_qdrant.py.
    """

    __tablename__ = "recipe_embeddings"

    recipe_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recipes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    # MD5 hash of all chunk texts — used to skip re-embedding when content unchanged
    embedding_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[EmbeddingStatus] = mapped_column(
        SQLAlchemyEnum(EmbeddingStatus, name="embeddingstatus"),
        nullable=False,
        default=EmbeddingStatus.PENDING,
    )
