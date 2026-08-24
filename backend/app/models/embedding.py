from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class RecipeEmbedding(TimestampMixin, Base):
    """
    Marker row — the actual vector lives in Qdrant, keyed by recipe_id.
    Compare updated_at against recipes.updated_at to detect stale embeddings.
    """

    __tablename__ = "recipe_embeddings"

    # recipe_id is both PK and FK — no surrogate id
    recipe_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recipes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    # Exact text that was embedded — used to detect content drift
    embedding_text: Mapped[str] = mapped_column(Text, nullable=False)
