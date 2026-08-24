import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.recipe import DifficultyLevel
from app.schemas.recipe.cook_log import CookLogOut
from app.schemas.recipe.image import RecipeImageIn, RecipeImageOut
from app.schemas.recipe.ingredient import RecipeIngredientIn, RecipeIngredientOut
from app.schemas.recipe.nutrition import NutritionIn, NutritionOut
from app.schemas.recipe.source import SourceIn, SourceOut
from app.schemas.recipe.step import RecipeStepIn, RecipeStepOut
from app.schemas.recipe.tag import TagIn, TagOut


class RecipeCreate(BaseModel):
    """
    Single-request creation. title is the only required field.
    All nested sections are best-effort — failures produce warnings, not errors.
    """
    title: str
    description: Optional[str] = None
    cuisine: Optional[str] = None
    difficulty: Optional[DifficultyLevel] = None
    servings: Optional[int] = Field(default=None, ge=1)
    prep_time_minutes: Optional[int] = Field(default=None, ge=0)
    cook_time_minutes: Optional[int] = Field(default=None, ge=0)
    notes: Optional[str] = None
    # Nested — all optional, best-effort
    steps: list[RecipeStepIn] = []
    ingredients: list[RecipeIngredientIn] = []
    images: list[RecipeImageIn] = []
    tags: list[TagIn] = []
    sources: list[SourceIn] = []
    nutrition: Optional[NutritionIn] = None


class RecipeUpdate(BaseModel):
    """Partial update of core fields only. Nested sections have their own endpoints."""
    title: Optional[str] = None
    description: Optional[str] = None
    cuisine: Optional[str] = None
    difficulty: Optional[DifficultyLevel] = None
    servings: Optional[int] = Field(default=None, ge=1)
    prep_time_minutes: Optional[int] = Field(default=None, ge=0)
    cook_time_minutes: Optional[int] = Field(default=None, ge=0)
    notes: Optional[str] = None


class RecipeSummary(BaseModel):
    """Lightweight — used in list view. No nested objects."""
    id: uuid.UUID
    title: str
    description: Optional[str]
    cuisine: Optional[str]
    difficulty: Optional[DifficultyLevel]
    total_time_minutes: Optional[int]
    is_favorite: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class RecipeOut(BaseModel):
    """Full detail — returned on create and get-by-id."""
    id: uuid.UUID
    title: str
    description: Optional[str]
    cuisine: Optional[str]
    difficulty: Optional[DifficultyLevel]
    servings: Optional[int]
    prep_time_minutes: Optional[int]
    cook_time_minutes: Optional[int]
    total_time_minutes: Optional[int]
    notes: Optional[str]
    is_favorite: bool
    steps: list[RecipeStepOut]
    ingredients: list[RecipeIngredientOut]
    images: list[RecipeImageOut]
    tags: list[TagOut]
    sources: list[SourceOut]
    nutrition: Optional[NutritionOut]
    created_at: datetime
    updated_at: datetime


class RecipeCreateResponse(BaseModel):
    recipe: RecipeOut
    warnings: dict[str, list[str]] = {}


class PaginatedRecipes(BaseModel):
    items: list[RecipeSummary]
    total: int
    page: int
    page_size: int
