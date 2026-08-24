import enum
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    Computed,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPkMixin


class DifficultyLevel(str, enum.Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"


class Recipe(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "recipes"

    owner_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cuisine: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    difficulty: Mapped[Optional[DifficultyLevel]] = mapped_column(
        SAEnum(DifficultyLevel, name="difficulty_level"), nullable=True, index=True
    )
    servings: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    prep_time_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cook_time_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_time_minutes: Mapped[Optional[int]] = mapped_column(
        Integer,
        Computed("prep_time_minutes + cook_time_minutes", persisted=True),
        nullable=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_favorite: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    # Populated by DB trigger — do not set from application code
    search_vector: Mapped[Optional[Any]] = mapped_column(TSVECTOR, nullable=True)

    __table_args__ = (
        Index("ix_recipes_search_vector", "search_vector", postgresql_using="gin"),
        Index(
            "ix_recipes_title_trgm",
            "title",
            postgresql_using="gin",
            postgresql_ops={"title": "gin_trgm_ops"},
        ),
    )


class RecipeStep(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "recipe_steps"

    recipe_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recipes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    instruction: Mapped[str] = mapped_column(Text, nullable=False)
    timer_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        UniqueConstraint("recipe_id", "step_number", name="uq_recipe_step_number"),
    )


class RecipeImage(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "recipe_images"

    recipe_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recipes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    is_primary: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    position: Mapped[int] = mapped_column(SmallInteger, server_default=text("0"), nullable=False)
