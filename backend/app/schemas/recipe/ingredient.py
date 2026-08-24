import uuid
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class RecipeIngredientIn(BaseModel):
    raw_name: str
    quantity: Optional[Decimal] = None
    unit: Optional[str] = None
    is_optional: bool = False
    ingredient_group: Optional[str] = None
    position: int = Field(ge=1)
    prep_note: Optional[str] = None


class RecipeIngredientCreate(BaseModel):
    raw_name: str
    quantity: Optional[Decimal] = None
    unit: Optional[str] = None
    is_optional: bool = False
    ingredient_group: Optional[str] = None
    position: int = Field(ge=1)
    prep_note: Optional[str] = None


class RecipeIngredientUpdate(BaseModel):
    raw_name: Optional[str] = None
    quantity: Optional[Decimal] = None
    unit: Optional[str] = None
    is_optional: Optional[bool] = None
    ingredient_group: Optional[str] = None
    position: Optional[int] = Field(default=None, ge=1)
    prep_note: Optional[str] = None


class RecipeIngredientOut(BaseModel):
    id: uuid.UUID
    raw_name: str
    quantity: Optional[Decimal]
    unit: Optional[str]
    is_optional: bool
    ingredient_group: Optional[str]
    position: int
    prep_note: Optional[str]

    model_config = {"from_attributes": True}
