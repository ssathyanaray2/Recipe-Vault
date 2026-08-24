from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Index, Numeric, SmallInteger, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPkMixin


class Ingredient(UUIDPkMixin, TimestampMixin, Base):
    """Canonical ingredient dictionary — shared across all users/recipes."""

    __tablename__ = "ingredients"

    canonical_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    # e.g. produce / protein / dairy / spice
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    __table_args__ = (
        Index(
            "ix_ingredients_canonical_name_trgm",
            "canonical_name",
            postgresql_using="gin",
            postgresql_ops={"canonical_name": "gin_trgm_ops"},
        ),
    )


class RecipeIngredient(UUIDPkMixin, TimestampMixin, Base):
    """Per-recipe ingredient usage — links a recipe to a canonical ingredient with quantity/unit."""

    __tablename__ = "recipe_ingredients"

    recipe_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recipes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Nullable: recipe can be saved before ingredient is resolved to canonical row
    ingredient_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ingredients.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Raw text as entered — e.g. "2 ripe bananas, mashed"
    raw_name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_optional: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    # e.g. "For the sauce"
    ingredient_group: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    # e.g. "finely chopped"
    prep_note: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    __table_args__ = (
        Index(
            "ix_recipe_ingredients_raw_name_trgm",
            "raw_name",
            postgresql_using="gin",
            postgresql_ops={"raw_name": "gin_trgm_ops"},
        ),
    )
