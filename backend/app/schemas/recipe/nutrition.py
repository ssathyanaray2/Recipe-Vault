from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class NutritionIn(BaseModel):
    calories: Optional[int] = None
    protein_g: Optional[Decimal] = None
    carbs_g: Optional[Decimal] = None
    fat_g: Optional[Decimal] = None
    fiber_g: Optional[Decimal] = None
    sugar_g: Optional[Decimal] = None
    sodium_mg: Optional[Decimal] = None
    per_serving: bool = True


class NutritionOut(BaseModel):
    calories: Optional[int]
    protein_g: Optional[Decimal]
    carbs_g: Optional[Decimal]
    fat_g: Optional[Decimal]
    fiber_g: Optional[Decimal]
    sugar_g: Optional[Decimal]
    sodium_mg: Optional[Decimal]
    per_serving: bool

    model_config = {"from_attributes": True}
