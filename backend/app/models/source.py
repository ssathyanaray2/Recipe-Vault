import enum
from typing import Optional

from sqlalchemy import Boolean, Enum as SAEnum, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPkMixin


class SourceType(str, enum.Enum):
    own = "own"
    website = "website"
    book = "book"
    family = "family"
    other = "other"


class Source(UUIDPkMixin, TimestampMixin, Base):
    """Canonical source dictionary — e.g. a cookbook, website, or family recipe box."""

    __tablename__ = "sources"

    source_type: Mapped[SourceType] = mapped_column(
        SAEnum(SourceType, name="source_type"), nullable=False
    )
    # e.g. "Serious Eats", "Ottolenghi: Simple", "Grandma's recipe box"
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    author: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        Index(
            "ix_sources_name_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
    )


class RecipeSource(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "recipe_sources"

    recipe_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recipes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean, server_default=text("true"), nullable=False
    )
