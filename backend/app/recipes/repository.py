"""
All raw DB queries for recipes and their related tables.
No business logic here — that lives in service.py.
"""
import uuid
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.cook_log import CookLog
from app.models.ingredient import Ingredient, RecipeIngredient
from app.models.nutrition import NutritionFacts
from app.models.recipe import Recipe, RecipeImage, RecipeStep
from app.models.source import RecipeSource, Source, SourceType
from app.models.tag import RecipeTag, Tag
from app.schemas.recipe import (
    CookLogCreate,
    NutritionIn,
    RecipeCreate,
    RecipeIngredientCreate,
    RecipeIngredientUpdate,
    RecipeStepCreate,
    RecipeStepUpdate,
    SourceUpdate,
    StepReorderItem,
)


# ---------------------------------------------------------------------------
# Core recipe
# ---------------------------------------------------------------------------

def get_by_id(db: Session, recipe_id: uuid.UUID, owner_id: uuid.UUID) -> Optional[Recipe]:
    return db.query(Recipe).filter(
        Recipe.id == recipe_id,
        Recipe.owner_id == owner_id,
    ).first()


def get_full(db: Session, recipe_id: uuid.UUID, owner_id: uuid.UUID) -> Optional[dict]:
    """
    Fetches recipe + all related objects in separate queries.
    Returns None if recipe not found or does not belong to owner.
    """
    recipe = get_by_id(db, recipe_id, owner_id)
    if not recipe:
        return None

    steps = (
        db.query(RecipeStep)
        .filter_by(recipe_id=recipe_id)
        .order_by(RecipeStep.step_number)
        .all()
    )
    ingredients = (
        db.query(RecipeIngredient)
        .filter_by(recipe_id=recipe_id)
        .order_by(RecipeIngredient.position)
        .all()
    )
    images = (
        db.query(RecipeImage)
        .filter_by(recipe_id=recipe_id)
        .order_by(RecipeImage.position)
        .all()
    )
    tags = (
        db.query(Tag)
        .join(RecipeTag, Tag.id == RecipeTag.tag_id)
        .filter(RecipeTag.recipe_id == recipe_id)
        .all()
    )
    # (RecipeSource, Source) tuples — SourceOut needs fields from both rows
    sources = (
        db.query(RecipeSource, Source)
        .join(Source, RecipeSource.source_id == Source.id)
        .filter(RecipeSource.recipe_id == recipe_id)
        .all()
    )
    nutrition = db.query(NutritionFacts).filter_by(recipe_id=recipe_id).first()

    return {
        "recipe": recipe,
        "steps": steps,
        "ingredients": ingredients,
        "images": images,
        "tags": tags,
        "sources": sources,
        "nutrition": nutrition,
    }


def list_by_owner(
    db: Session,
    owner_id: uuid.UUID,
    page: int,
    page_size: int,
) -> tuple[list[Recipe], int]:
    q = db.query(Recipe).filter(Recipe.owner_id == owner_id)
    total = q.count()
    items = (
        q.order_by(Recipe.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total


def create(db: Session, owner_id: uuid.UUID, data: RecipeCreate) -> Recipe:
    recipe = Recipe(
        owner_id=owner_id,
        title=data.title,
        description=data.description,
        cuisine=data.cuisine,
        difficulty=data.difficulty,
        servings=data.servings,
        prep_time_minutes=data.prep_time_minutes,
        cook_time_minutes=data.cook_time_minutes,
        notes=data.notes,
    )
    db.add(recipe)
    db.flush()  # get recipe.id without committing — nested objects added next
    return recipe


def update(db: Session, recipe: Recipe, data) -> Recipe:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(recipe, field, value)
    db.commit()
    db.refresh(recipe)
    return recipe


def delete(db: Session, recipe: Recipe) -> None:
    db.delete(recipe)
    db.commit()


def toggle_favorite(db: Session, recipe: Recipe) -> Recipe:
    recipe.is_favorite = not recipe.is_favorite
    db.commit()
    db.refresh(recipe)
    return recipe


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------

def get_step(
    db: Session, step_id: uuid.UUID, recipe_id: uuid.UUID
) -> Optional[RecipeStep]:
    return db.query(RecipeStep).filter(
        RecipeStep.id == step_id,
        RecipeStep.recipe_id == recipe_id,
    ).first()


def create_step(
    db: Session, recipe_id: uuid.UUID, data: RecipeStepCreate
) -> RecipeStep:
    step = RecipeStep(
        recipe_id=recipe_id,
        step_number=data.step_number,
        instruction=data.instruction,
        timer_seconds=data.timer_seconds,
    )
    db.add(step)
    db.commit()
    db.refresh(step)
    return step


def update_step(
    db: Session, step: RecipeStep, data: RecipeStepUpdate
) -> RecipeStep:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(step, field, value)
    db.commit()
    db.refresh(step)
    return step


def delete_step(db: Session, step: RecipeStep) -> None:
    db.delete(step)
    db.commit()


def reorder_steps(
    db: Session, recipe_id: uuid.UUID, items: list[StepReorderItem]
) -> None:
    for item in items:
        step = get_step(db, item.step_id, recipe_id)
        if step:
            step.step_number = item.step_number
    db.commit()


# ---------------------------------------------------------------------------
# Ingredients — canonical resolution via trigram similarity
# ---------------------------------------------------------------------------

def find_canonical_ingredient(db: Session, name: str) -> Optional[Ingredient]:
    """Trigram similarity search against canonical ingredient names."""
    return (
        db.query(Ingredient)
        .filter(func.similarity(Ingredient.canonical_name, name) > 0.3)
        .order_by(func.similarity(Ingredient.canonical_name, name).desc())
        .first()
    )


def get_or_create_ingredient(db: Session, raw_name: str) -> Ingredient:
    match = find_canonical_ingredient(db, raw_name)
    if match:
        return match
    ingredient = Ingredient(canonical_name=raw_name.lower().strip())
    db.add(ingredient)
    db.flush()
    return ingredient


def get_recipe_ingredient(
    db: Session, ingredient_id: uuid.UUID, recipe_id: uuid.UUID
) -> Optional[RecipeIngredient]:
    return db.query(RecipeIngredient).filter(
        RecipeIngredient.id == ingredient_id,
        RecipeIngredient.recipe_id == recipe_id,
    ).first()


def create_recipe_ingredient(
    db: Session,
    recipe_id: uuid.UUID,
    data: RecipeIngredientCreate,
    canonical_id: Optional[uuid.UUID],
) -> RecipeIngredient:
    ri = RecipeIngredient(
        recipe_id=recipe_id,
        ingredient_id=canonical_id,
        raw_name=data.raw_name,
        quantity=data.quantity,
        unit=data.unit,
        is_optional=data.is_optional,
        ingredient_group=data.ingredient_group,
        position=data.position,
        prep_note=data.prep_note,
    )
    db.add(ri)
    db.commit()
    db.refresh(ri)
    return ri


def update_recipe_ingredient(
    db: Session, ri: RecipeIngredient, data: RecipeIngredientUpdate
) -> RecipeIngredient:
    updates = data.model_dump(exclude_unset=True)
    if "raw_name" in updates:
        # Re-resolve canonical ingredient when raw_name changes
        canonical = get_or_create_ingredient(db, updates["raw_name"])
        ri.ingredient_id = canonical.id
    for field, value in updates.items():
        setattr(ri, field, value)
    db.commit()
    db.refresh(ri)
    return ri


def delete_recipe_ingredient(db: Session, ri: RecipeIngredient) -> None:
    db.delete(ri)
    db.commit()


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------

def get_or_create_tag(db: Session, name: str, category: str) -> Tag:
    normalized = name.lower().strip()
    tag = db.query(Tag).filter(func.lower(Tag.name) == normalized).first()
    if not tag:
        tag = Tag(name=normalized, category=category)
        db.add(tag)
        db.flush()
    return tag


def get_recipe_tag(
    db: Session, recipe_id: uuid.UUID, tag_id: uuid.UUID
) -> Optional[RecipeTag]:
    return db.query(RecipeTag).filter(
        RecipeTag.recipe_id == recipe_id,
        RecipeTag.tag_id == tag_id,
    ).first()


def add_recipe_tag(
    db: Session, recipe_id: uuid.UUID, tag_id: uuid.UUID
) -> RecipeTag:
    rt = RecipeTag(recipe_id=recipe_id, tag_id=tag_id)
    db.add(rt)
    db.commit()
    return rt


def remove_recipe_tag(db: Session, rt: RecipeTag) -> None:
    db.delete(rt)
    db.commit()


# ---------------------------------------------------------------------------
# Sources — canonical resolution via trigram similarity
# ---------------------------------------------------------------------------

def find_canonical_source(
    db: Session, name: str, source_type: SourceType
) -> Optional[Source]:
    """
    Trigram similarity scoped by source_type.
    Higher threshold (0.4) than ingredients — source names are more specific.
    "Serious Eats Website" will still match "Serious Eats".
    """
    return (
        db.query(Source)
        .filter(
            Source.source_type == source_type,
            func.similarity(Source.name, name) > 0.4,
        )
        .order_by(func.similarity(Source.name, name).desc())
        .first()
    )


def get_or_create_source(
    db: Session,
    name: str,
    source_type: SourceType,
    author: Optional[str] = None,
    url: Optional[str] = None,
) -> Source:
    match = find_canonical_source(db, name, source_type)
    if match:
        return match
    source = Source(source_type=source_type, name=name, author=author, url=url)
    db.add(source)
    db.flush()
    return source


def get_recipe_source(
    db: Session, recipe_source_id: uuid.UUID, recipe_id: uuid.UUID
) -> Optional[RecipeSource]:
    return db.query(RecipeSource).filter(
        RecipeSource.id == recipe_source_id,
        RecipeSource.recipe_id == recipe_id,
    ).first()


def add_recipe_source(
    db: Session, recipe_id: uuid.UUID, source_id: uuid.UUID, is_primary: bool
) -> RecipeSource:
    rs = RecipeSource(recipe_id=recipe_id, source_id=source_id, is_primary=is_primary)
    db.add(rs)
    db.commit()
    db.refresh(rs)
    return rs


def update_recipe_source(
    db: Session, rs: RecipeSource, data: SourceUpdate
) -> RecipeSource:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(rs, field, value)
    db.commit()
    db.refresh(rs)
    return rs


def remove_recipe_source(db: Session, rs: RecipeSource) -> None:
    db.delete(rs)
    db.commit()


# ---------------------------------------------------------------------------
# Images
# ---------------------------------------------------------------------------

def get_image(
    db: Session, image_id: uuid.UUID, recipe_id: uuid.UUID
) -> Optional[RecipeImage]:
    return db.query(RecipeImage).filter(
        RecipeImage.id == image_id,
        RecipeImage.recipe_id == recipe_id,
    ).first()


def add_image(db: Session, recipe_id: uuid.UUID, data) -> RecipeImage:
    image = RecipeImage(
        recipe_id=recipe_id,
        url=data.url,
        is_primary=data.is_primary,
        position=data.position,
    )
    db.add(image)
    db.commit()
    db.refresh(image)
    return image


def delete_image(db: Session, image: RecipeImage) -> None:
    db.delete(image)
    db.commit()


# ---------------------------------------------------------------------------
# Nutrition
# ---------------------------------------------------------------------------

def upsert_nutrition(
    db: Session, recipe_id: uuid.UUID, data: NutritionIn
) -> NutritionFacts:
    nutrition = db.query(NutritionFacts).filter_by(recipe_id=recipe_id).first()
    if nutrition:
        for field, value in data.model_dump().items():
            setattr(nutrition, field, value)
    else:
        nutrition = NutritionFacts(recipe_id=recipe_id, **data.model_dump())
        db.add(nutrition)
    db.commit()
    db.refresh(nutrition)
    return nutrition


# ---------------------------------------------------------------------------
# Cook logs
# ---------------------------------------------------------------------------

def create_cook_log(
    db: Session,
    recipe_id: uuid.UUID,
    user_id: uuid.UUID,
    data: CookLogCreate,
) -> CookLog:
    log = CookLog(
        recipe_id=recipe_id,
        user_id=user_id,
        rating=data.rating,
        notes=data.notes,
    )
    if data.cooked_at:
        log.cooked_at = data.cooked_at
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def list_cook_logs(db: Session, recipe_id: uuid.UUID) -> list[CookLog]:
    return (
        db.query(CookLog)
        .filter_by(recipe_id=recipe_id)
        .order_by(CookLog.cooked_at.desc())
        .all()
    )
