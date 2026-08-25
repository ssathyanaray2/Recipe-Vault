"""
Business logic for recipes.
Coordinates repository calls; no raw DB queries here.
"""
import logging
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError

logger = logging.getLogger(__name__)
from app.models.recipe import Recipe
from app.models.source import RecipeSource, Source
from app.recipes import repository as repo
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
    RecipeSummary,
    RecipeUpdate,
    SourceIn,
    SourceOut,
    SourceUpdate,
    StepReorderItem,
    TagIn,
    TagOut,
)
from app.schemas.recipe.step import RecipeStepCreate, RecipeStepOut, RecipeStepUpdate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _trigger_ingestion(db: Session, recipe_id: uuid.UUID) -> None:
    """
    Mark the embedding row as PENDING, then fire Celery.
    Writing PENDING before the task fires means any unstarted job is visible
    in the dead-letter query (status=PENDING, updated_at old).
    """
    from app.models.embedding import EmbeddingStatus, RecipeEmbedding

    marker = db.get(RecipeEmbedding, recipe_id)
    if marker:
        marker.status = EmbeddingStatus.PENDING
    else:
        db.add(RecipeEmbedding(
            recipe_id=recipe_id,
            model_name="",        # filled in by pipeline on success
            embedding_text="",
            status=EmbeddingStatus.PENDING,
        ))
    db.commit()

    try:
        from app.ingestion.tasks import ingest_recipe
        ingest_recipe.delay(str(recipe_id))
    except Exception:
        logger.warning("Could not queue ingestion task for recipe %s", recipe_id)

def _source_out(rs: RecipeSource, source: Source) -> SourceOut:
    return SourceOut(
        id=rs.id,
        source_type=source.source_type,
        name=source.name,
        author=source.author,
        url=source.url,
        is_primary=rs.is_primary,
    )


def _build_recipe_out(full: dict) -> RecipeOut:
    recipe = full["recipe"]
    sources = [_source_out(rs, src) for rs, src in full["sources"]]
    return RecipeOut(
        id=recipe.id,
        title=recipe.title,
        description=recipe.description,
        cuisine=recipe.cuisine,
        difficulty=recipe.difficulty,
        servings=recipe.servings,
        prep_time_minutes=recipe.prep_time_minutes,
        cook_time_minutes=recipe.cook_time_minutes,
        total_time_minutes=recipe.total_time_minutes,
        notes=recipe.notes,
        is_favorite=recipe.is_favorite,
        steps=[RecipeStepOut.model_validate(s) for s in full["steps"]],
        ingredients=[RecipeIngredientOut.model_validate(i) for i in full["ingredients"]],
        images=[RecipeImageOut.model_validate(img) for img in full["images"]],
        tags=[TagOut.model_validate(t) for t in full["tags"]],
        sources=sources,
        nutrition=NutritionOut.model_validate(full["nutrition"]) if full["nutrition"] else None,
        created_at=recipe.created_at,
        updated_at=recipe.updated_at,
    )


def _require_recipe(db: Session, recipe_id: uuid.UUID, owner_id: uuid.UUID) -> Recipe:
    recipe = repo.get_by_id(db, recipe_id, owner_id)
    if not recipe:
        raise NotFoundError("Recipe not found")
    return recipe


def _require_full(db: Session, recipe_id: uuid.UUID, owner_id: uuid.UUID) -> dict:
    full = repo.get_full(db, recipe_id, owner_id)
    if not full:
        raise NotFoundError("Recipe not found")
    return full


# ---------------------------------------------------------------------------
# Core recipe
# ---------------------------------------------------------------------------

def create_recipe(
    db: Session,
    owner_id: uuid.UUID,
    data: RecipeCreate,
) -> RecipeCreateResponse:
    """
    Best-effort creation: only title is required.
    Each nested section is attempted independently; failures collected as warnings.
    Everything commits in one transaction.
    """
    warnings: dict[str, list[str]] = {}

    recipe = repo.create(db, owner_id, data)  # flush only — no commit yet
    recipe_id = recipe.id

    # Steps
    step_warnings: list[str] = []
    for s in data.steps:
        try:
            _create_step_no_commit(db, recipe_id, RecipeStepCreate(
                step_number=s.step_number,
                instruction=s.instruction,
                timer_seconds=s.timer_seconds,
            ))
        except Exception as exc:
            step_warnings.append(f"Step {s.step_number}: {exc}")
    if step_warnings:
        warnings["steps"] = step_warnings

    # Ingredients
    ingredient_warnings: list[str] = []
    for ing in data.ingredients:
        try:
            canonical = repo.get_or_create_ingredient(db, ing.raw_name)
            _create_recipe_ingredient_no_commit(db, recipe_id, RecipeIngredientCreate(
                raw_name=ing.raw_name,
                quantity=ing.quantity,
                unit=ing.unit,
                is_optional=ing.is_optional,
                ingredient_group=ing.ingredient_group,
                position=ing.position,
                prep_note=ing.prep_note,
            ), canonical.id)
        except Exception as exc:
            ingredient_warnings.append(f"Ingredient '{ing.raw_name}': {exc}")
    if ingredient_warnings:
        warnings["ingredients"] = ingredient_warnings

    # Images
    image_warnings: list[str] = []
    for img in data.images:
        try:
            _add_image_no_commit(db, recipe_id, img)
        except Exception as exc:
            image_warnings.append(f"Image '{img.url}': {exc}")
    if image_warnings:
        warnings["images"] = image_warnings

    # Tags
    tag_warnings: list[str] = []
    for tag_in in data.tags:
        try:
            tag = repo.get_or_create_tag(db, tag_in.name, tag_in.category)
            existing = repo.get_recipe_tag(db, recipe_id, tag.id)
            if not existing:
                _add_recipe_tag_no_commit(db, recipe_id, tag.id)
        except Exception as exc:
            tag_warnings.append(f"Tag '{tag_in.name}': {exc}")
    if tag_warnings:
        warnings["tags"] = tag_warnings

    # Sources
    source_warnings: list[str] = []
    for src_in in data.sources:
        try:
            source = repo.get_or_create_source(
                db, src_in.name, src_in.source_type, src_in.author, src_in.url
            )
            _add_recipe_source_no_commit(db, recipe_id, source.id, src_in.is_primary)
        except Exception as exc:
            source_warnings.append(f"Source '{src_in.name}': {exc}")
    if source_warnings:
        warnings["sources"] = source_warnings

    # Nutrition
    if data.nutrition:
        try:
            _upsert_nutrition_no_commit(db, recipe_id, data.nutrition)
        except Exception as exc:
            warnings["nutrition"] = [str(exc)]

    # Single commit for everything
    db.commit()
    db.refresh(recipe)

    _trigger_ingestion(db, recipe_id)

    full = _require_full(db, recipe_id, owner_id)
    return RecipeCreateResponse(recipe=_build_recipe_out(full), warnings=warnings)


def get_recipe(
    db: Session, recipe_id: uuid.UUID, owner_id: uuid.UUID
) -> RecipeOut:
    full = _require_full(db, recipe_id, owner_id)
    return _build_recipe_out(full)


def list_recipes(
    db: Session,
    owner_id: uuid.UUID,
    page: int,
    page_size: int,
) -> PaginatedRecipes:
    items, total = repo.list_by_owner(db, owner_id, page, page_size)
    return PaginatedRecipes(
        items=[RecipeSummary.model_validate(r) for r in items],
        total=total,
        page=page,
        page_size=page_size,
    )


def update_recipe(
    db: Session,
    recipe_id: uuid.UUID,
    owner_id: uuid.UUID,
    data: RecipeUpdate,
) -> RecipeOut:
    recipe = _require_recipe(db, recipe_id, owner_id)
    repo.update(db, recipe, data)
    _trigger_ingestion(db, recipe_id)
    full = _require_full(db, recipe_id, owner_id)
    return _build_recipe_out(full)


def delete_recipe(
    db: Session, recipe_id: uuid.UUID, owner_id: uuid.UUID
) -> None:
    recipe = _require_recipe(db, recipe_id, owner_id)
    try:
        from app.vectorstore.qdrant import QdrantVectorStore
        QdrantVectorStore().delete_by_recipe(str(recipe_id))
    except Exception:
        logger.warning("Could not delete Qdrant vectors for recipe %s — vectors may be orphaned", recipe_id)
    repo.delete(db, recipe)


def toggle_favorite(
    db: Session, recipe_id: uuid.UUID, owner_id: uuid.UUID
) -> RecipeOut:
    recipe = _require_recipe(db, recipe_id, owner_id)
    repo.toggle_favorite(db, recipe)
    full = _require_full(db, recipe_id, owner_id)
    return _build_recipe_out(full)


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------

def add_step(
    db: Session,
    recipe_id: uuid.UUID,
    owner_id: uuid.UUID,
    data: RecipeStepCreate,
) -> RecipeStepOut:
    _require_recipe(db, recipe_id, owner_id)
    step = repo.create_step(db, recipe_id, data)
    return RecipeStepOut.model_validate(step)


def update_step(
    db: Session,
    recipe_id: uuid.UUID,
    step_id: uuid.UUID,
    owner_id: uuid.UUID,
    data: RecipeStepUpdate,
) -> RecipeStepOut:
    _require_recipe(db, recipe_id, owner_id)
    step = repo.get_step(db, step_id, recipe_id)
    if not step:
        raise NotFoundError("Step not found")
    step = repo.update_step(db, step, data)
    return RecipeStepOut.model_validate(step)


def delete_step(
    db: Session,
    recipe_id: uuid.UUID,
    step_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> None:
    _require_recipe(db, recipe_id, owner_id)
    step = repo.get_step(db, step_id, recipe_id)
    if not step:
        raise NotFoundError("Step not found")
    repo.delete_step(db, step)


def reorder_steps(
    db: Session,
    recipe_id: uuid.UUID,
    owner_id: uuid.UUID,
    items: list[StepReorderItem],
) -> RecipeOut:
    _require_recipe(db, recipe_id, owner_id)
    repo.reorder_steps(db, recipe_id, items)
    full = _require_full(db, recipe_id, owner_id)
    return _build_recipe_out(full)


# ---------------------------------------------------------------------------
# Ingredients
# ---------------------------------------------------------------------------

def add_ingredient(
    db: Session,
    recipe_id: uuid.UUID,
    owner_id: uuid.UUID,
    data: RecipeIngredientCreate,
) -> RecipeIngredientOut:
    _require_recipe(db, recipe_id, owner_id)
    canonical = repo.get_or_create_ingredient(db, data.raw_name)
    ri = repo.create_recipe_ingredient(db, recipe_id, data, canonical.id)
    return RecipeIngredientOut.model_validate(ri)


def update_ingredient(
    db: Session,
    recipe_id: uuid.UUID,
    ingredient_id: uuid.UUID,
    owner_id: uuid.UUID,
    data: RecipeIngredientUpdate,
) -> RecipeIngredientOut:
    _require_recipe(db, recipe_id, owner_id)
    ri = repo.get_recipe_ingredient(db, ingredient_id, recipe_id)
    if not ri:
        raise NotFoundError("Ingredient not found")
    ri = repo.update_recipe_ingredient(db, ri, data)
    return RecipeIngredientOut.model_validate(ri)


def delete_ingredient(
    db: Session,
    recipe_id: uuid.UUID,
    ingredient_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> None:
    _require_recipe(db, recipe_id, owner_id)
    ri = repo.get_recipe_ingredient(db, ingredient_id, recipe_id)
    if not ri:
        raise NotFoundError("Ingredient not found")
    repo.delete_recipe_ingredient(db, ri)


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------

def add_tag(
    db: Session,
    recipe_id: uuid.UUID,
    owner_id: uuid.UUID,
    data: TagIn,
) -> TagOut:
    _require_recipe(db, recipe_id, owner_id)
    tag = repo.get_or_create_tag(db, data.name, data.category)
    existing = repo.get_recipe_tag(db, recipe_id, tag.id)
    if existing:
        raise ConflictError("Tag already attached to recipe")
    repo.add_recipe_tag(db, recipe_id, tag.id)
    return TagOut.model_validate(tag)


def remove_tag(
    db: Session,
    recipe_id: uuid.UUID,
    tag_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> None:
    _require_recipe(db, recipe_id, owner_id)
    rt = repo.get_recipe_tag(db, recipe_id, tag_id)
    if not rt:
        raise NotFoundError("Tag not found on recipe")
    repo.remove_recipe_tag(db, rt)


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------

def add_source(
    db: Session,
    recipe_id: uuid.UUID,
    owner_id: uuid.UUID,
    data: SourceIn,
) -> SourceOut:
    _require_recipe(db, recipe_id, owner_id)
    source = repo.get_or_create_source(
        db, data.name, data.source_type, data.author, data.url
    )
    rs = repo.add_recipe_source(db, recipe_id, source.id, data.is_primary)
    return _source_out(rs, source)


def update_source(
    db: Session,
    recipe_id: uuid.UUID,
    recipe_source_id: uuid.UUID,
    owner_id: uuid.UUID,
    data: SourceUpdate,
) -> SourceOut:
    _require_recipe(db, recipe_id, owner_id)
    rs = repo.get_recipe_source(db, recipe_source_id, recipe_id)
    if not rs:
        raise NotFoundError("Source not found on recipe")
    rs = repo.update_recipe_source(db, rs, data)
    source = db.get(Source, rs.source_id)
    return _source_out(rs, source)


def remove_source(
    db: Session,
    recipe_id: uuid.UUID,
    recipe_source_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> None:
    _require_recipe(db, recipe_id, owner_id)
    rs = repo.get_recipe_source(db, recipe_source_id, recipe_id)
    if not rs:
        raise NotFoundError("Source not found on recipe")
    repo.remove_recipe_source(db, rs)


# ---------------------------------------------------------------------------
# Images
# ---------------------------------------------------------------------------

def add_image(
    db: Session,
    recipe_id: uuid.UUID,
    owner_id: uuid.UUID,
    data: RecipeImageIn,
) -> RecipeImageOut:
    _require_recipe(db, recipe_id, owner_id)
    image = repo.add_image(db, recipe_id, data)
    return RecipeImageOut.model_validate(image)


def delete_image(
    db: Session,
    recipe_id: uuid.UUID,
    image_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> None:
    _require_recipe(db, recipe_id, owner_id)
    image = repo.get_image(db, image_id, recipe_id)
    if not image:
        raise NotFoundError("Image not found")
    repo.delete_image(db, image)


# ---------------------------------------------------------------------------
# Nutrition
# ---------------------------------------------------------------------------

def upsert_nutrition(
    db: Session,
    recipe_id: uuid.UUID,
    owner_id: uuid.UUID,
    data: NutritionIn,
) -> NutritionOut:
    _require_recipe(db, recipe_id, owner_id)
    nutrition = repo.upsert_nutrition(db, recipe_id, data)
    return NutritionOut.model_validate(nutrition)


# ---------------------------------------------------------------------------
# Cook logs
# ---------------------------------------------------------------------------

def log_cook(
    db: Session,
    recipe_id: uuid.UUID,
    owner_id: uuid.UUID,
    data: CookLogCreate,
) -> CookLogOut:
    _require_recipe(db, recipe_id, owner_id)
    log = repo.create_cook_log(db, recipe_id, owner_id, data)
    return CookLogOut.model_validate(log)


def list_cook_logs(
    db: Session,
    recipe_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> list[CookLogOut]:
    _require_recipe(db, recipe_id, owner_id)
    logs = repo.list_cook_logs(db, recipe_id)
    return [CookLogOut.model_validate(log) for log in logs]


# ---------------------------------------------------------------------------
# No-commit helpers for best-effort create (avoid intermediate commits)
# ---------------------------------------------------------------------------

def _create_step_no_commit(db, recipe_id, data):
    from app.models.recipe import RecipeStep
    step = RecipeStep(
        recipe_id=recipe_id,
        step_number=data.step_number,
        instruction=data.instruction,
        timer_seconds=data.timer_seconds,
    )
    db.add(step)
    db.flush()
    return step


def _create_recipe_ingredient_no_commit(db, recipe_id, data, canonical_id):
    from app.models.ingredient import RecipeIngredient
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
    db.flush()
    return ri


def _add_image_no_commit(db, recipe_id, data):
    from app.models.recipe import RecipeImage
    image = RecipeImage(
        recipe_id=recipe_id,
        url=data.url,
        is_primary=data.is_primary,
        position=data.position,
    )
    db.add(image)
    db.flush()
    return image


def _add_recipe_tag_no_commit(db, recipe_id, tag_id):
    from app.models.tag import RecipeTag
    rt = RecipeTag(recipe_id=recipe_id, tag_id=tag_id)
    db.add(rt)
    db.flush()
    return rt


def _add_recipe_source_no_commit(db, recipe_id, source_id, is_primary):
    from app.models.source import RecipeSource
    rs = RecipeSource(recipe_id=recipe_id, source_id=source_id, is_primary=is_primary)
    db.add(rs)
    db.flush()
    return rs


def _upsert_nutrition_no_commit(db, recipe_id, data):
    from app.models.nutrition import NutritionFacts
    nutrition = db.query(NutritionFacts).filter_by(recipe_id=recipe_id).first()
    if nutrition:
        for field, value in data.model_dump().items():
            setattr(nutrition, field, value)
    else:
        nutrition = NutritionFacts(recipe_id=recipe_id, **data.model_dump())
        db.add(nutrition)
    db.flush()
    return nutrition
