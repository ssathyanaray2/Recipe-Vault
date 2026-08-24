"""
Recipe routes — thin handlers that delegate to service.py.
All routes require authentication via get_current_user.
"""
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.recipes import service
from app.schemas.recipe import (
    CookLogCreate,
    CookLogOut,
    NutritionIn,
    NutritionOut,
    PaginatedRecipes,
    RecipeCreate,
    RecipeCreateResponse,
    RecipeImageIn,
    RecipeImageOut,
    RecipeIngredientCreate,
    RecipeIngredientOut,
    RecipeIngredientUpdate,
    RecipeOut,
    RecipeUpdate,
    SourceIn,
    SourceOut,
    SourceUpdate,
    StepReorderItem,
    TagIn,
    TagOut,
)
from app.schemas.recipe.step import RecipeStepCreate, RecipeStepOut, RecipeStepUpdate

router = APIRouter(prefix="/recipes", tags=["recipes"])


# ---------------------------------------------------------------------------
# Core recipe
# ---------------------------------------------------------------------------

@router.post("", response_model=RecipeCreateResponse, status_code=status.HTTP_201_CREATED)
def create_recipe(
    data: RecipeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.create_recipe(db, current_user.id, data)


@router.get("", response_model=PaginatedRecipes)
def list_recipes(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.list_recipes(db, current_user.id, page, page_size)


@router.get("/{recipe_id}", response_model=RecipeOut)
def get_recipe(
    recipe_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.get_recipe(db, recipe_id, current_user.id)


@router.patch("/{recipe_id}", response_model=RecipeOut)
def update_recipe(
    recipe_id: uuid.UUID,
    data: RecipeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.update_recipe(db, recipe_id, current_user.id, data)


@router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recipe(
    recipe_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service.delete_recipe(db, recipe_id, current_user.id)


@router.post("/{recipe_id}/favorite", response_model=RecipeOut)
def toggle_favorite(
    recipe_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.toggle_favorite(db, recipe_id, current_user.id)


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------

@router.post("/{recipe_id}/steps", response_model=RecipeStepOut, status_code=status.HTTP_201_CREATED)
def add_step(
    recipe_id: uuid.UUID,
    data: RecipeStepCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.add_step(db, recipe_id, current_user.id, data)


@router.patch("/{recipe_id}/steps/{step_id}", response_model=RecipeStepOut)
def update_step(
    recipe_id: uuid.UUID,
    step_id: uuid.UUID,
    data: RecipeStepUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.update_step(db, recipe_id, step_id, current_user.id, data)


@router.delete("/{recipe_id}/steps/{step_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_step(
    recipe_id: uuid.UUID,
    step_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service.delete_step(db, recipe_id, step_id, current_user.id)


@router.put("/{recipe_id}/steps/reorder", response_model=RecipeOut)
def reorder_steps(
    recipe_id: uuid.UUID,
    items: list[StepReorderItem],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.reorder_steps(db, recipe_id, current_user.id, items)


# ---------------------------------------------------------------------------
# Ingredients
# ---------------------------------------------------------------------------

@router.post("/{recipe_id}/ingredients", response_model=RecipeIngredientOut, status_code=status.HTTP_201_CREATED)
def add_ingredient(
    recipe_id: uuid.UUID,
    data: RecipeIngredientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.add_ingredient(db, recipe_id, current_user.id, data)


@router.patch("/{recipe_id}/ingredients/{ingredient_id}", response_model=RecipeIngredientOut)
def update_ingredient(
    recipe_id: uuid.UUID,
    ingredient_id: uuid.UUID,
    data: RecipeIngredientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.update_ingredient(db, recipe_id, ingredient_id, current_user.id, data)


@router.delete("/{recipe_id}/ingredients/{ingredient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ingredient(
    recipe_id: uuid.UUID,
    ingredient_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service.delete_ingredient(db, recipe_id, ingredient_id, current_user.id)


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------

@router.post("/{recipe_id}/tags", response_model=TagOut, status_code=status.HTTP_201_CREATED)
def add_tag(
    recipe_id: uuid.UUID,
    data: TagIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.add_tag(db, recipe_id, current_user.id, data)


@router.delete("/{recipe_id}/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_tag(
    recipe_id: uuid.UUID,
    tag_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service.remove_tag(db, recipe_id, tag_id, current_user.id)


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------

@router.post("/{recipe_id}/sources", response_model=SourceOut, status_code=status.HTTP_201_CREATED)
def add_source(
    recipe_id: uuid.UUID,
    data: SourceIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.add_source(db, recipe_id, current_user.id, data)


@router.patch("/{recipe_id}/sources/{recipe_source_id}", response_model=SourceOut)
def update_source(
    recipe_id: uuid.UUID,
    recipe_source_id: uuid.UUID,
    data: SourceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.update_source(db, recipe_id, recipe_source_id, current_user.id, data)


@router.delete("/{recipe_id}/sources/{recipe_source_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_source(
    recipe_id: uuid.UUID,
    recipe_source_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service.remove_source(db, recipe_id, recipe_source_id, current_user.id)


# ---------------------------------------------------------------------------
# Images
# ---------------------------------------------------------------------------

@router.post("/{recipe_id}/images", response_model=RecipeImageOut, status_code=status.HTTP_201_CREATED)
def add_image(
    recipe_id: uuid.UUID,
    data: RecipeImageIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.add_image(db, recipe_id, current_user.id, data)


@router.delete("/{recipe_id}/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_image(
    recipe_id: uuid.UUID,
    image_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service.delete_image(db, recipe_id, image_id, current_user.id)


# ---------------------------------------------------------------------------
# Nutrition
# ---------------------------------------------------------------------------

@router.put("/{recipe_id}/nutrition", response_model=NutritionOut)
def upsert_nutrition(
    recipe_id: uuid.UUID,
    data: NutritionIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.upsert_nutrition(db, recipe_id, current_user.id, data)


# ---------------------------------------------------------------------------
# Cook logs
# ---------------------------------------------------------------------------

@router.post("/{recipe_id}/cook-logs", response_model=CookLogOut, status_code=status.HTTP_201_CREATED)
def log_cook(
    recipe_id: uuid.UUID,
    data: CookLogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.log_cook(db, recipe_id, current_user.id, data)


@router.get("/{recipe_id}/cook-logs", response_model=list[CookLogOut])
def list_cook_logs(
    recipe_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.list_cook_logs(db, recipe_id, current_user.id)
