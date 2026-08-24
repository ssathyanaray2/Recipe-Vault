from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NutritionFacts(Base):
    """Optional 1:1 with recipes. recipe_id is both PK and FK — no surrogate id."""

    __tablename__ = "nutrition_facts"

    recipe_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recipes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    calories: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    protein_g: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2), nullable=True)
    carbs_g: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2), nullable=True)
    fat_g: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2), nullable=True)
    fiber_g: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2), nullable=True)
    sugar_g: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2), nullable=True)
    sodium_mg: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2), nullable=True)
    per_serving: Mapped[bool] = mapped_column(
        Boolean, server_default=text("true"), nullable=False
    )
