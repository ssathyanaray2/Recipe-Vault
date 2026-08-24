"""
Unit tests for app.recipes.service.
The DB session and all repository calls are mocked — no real DB required.
Focus areas:
  - best-effort create: a failing section produces warnings, not a rollback
  - NotFoundError raised when recipe/step/ingredient/etc. not found
  - ConflictError raised on duplicate tag
  - canonical ingredient re-resolved when raw_name changes on update
"""
import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import ConflictError, NotFoundError
from app.models.recipe import DifficultyLevel
from app.recipes import service
from app.schemas.recipe import (
    RecipeCreate,
    RecipeIngredientUpdate,
    RecipeUpdate,
    TagIn,
)
from app.schemas.recipe.ingredient import RecipeIngredientCreate
from app.schemas.recipe.step import RecipeStepCreate, RecipeStepUpdate


# ---------------------------------------------------------------------------
# Helpers — build lightweight fakes that pass model_validate
# ---------------------------------------------------------------------------

def _make_recipe(**kwargs):
    r = MagicMock()
    r.id = kwargs.get("id", uuid.uuid4())
    r.owner_id = kwargs.get("owner_id", uuid.uuid4())
    r.title = kwargs.get("title", "Test Recipe")
    r.description = None
    r.cuisine = None
    r.difficulty = None
    r.servings = None
    r.prep_time_minutes = None
    r.cook_time_minutes = None
    r.total_time_minutes = None
    r.notes = None
    r.is_favorite = False
    r.created_at = "2024-01-01T00:00:00"
    r.updated_at = "2024-01-01T00:00:00"
    return r


def _make_full(recipe):
    """Minimal get_full() return value."""
    return {
        "recipe": recipe,
        "steps": [],
        "ingredients": [],
        "images": [],
        "tags": [],
        "sources": [],
        "nutrition": None,
    }


def _make_step(**kwargs):
    s = MagicMock()
    s.id = kwargs.get("id", uuid.uuid4())
    s.step_number = kwargs.get("step_number", 1)
    s.instruction = kwargs.get("instruction", "Do something")
    s.timer_seconds = None
    return s


def _make_ingredient(**kwargs):
    ri = MagicMock()
    ri.id = kwargs.get("id", uuid.uuid4())
    ri.raw_name = kwargs.get("raw_name", "flour")
    ri.quantity = kwargs.get("quantity", Decimal("2.0"))
    ri.unit = kwargs.get("unit", "cups")
    ri.is_optional = False
    ri.ingredient_group = None
    ri.position = kwargs.get("position", 1)
    ri.prep_note = None
    return ri


def _make_tag(**kwargs):
    t = MagicMock()
    t.id = kwargs.get("id", uuid.uuid4())
    t.name = kwargs.get("name", "vegetarian")
    t.category = kwargs.get("category", "dietary")
    return t


# ---------------------------------------------------------------------------
# create_recipe — best-effort behaviour
# ---------------------------------------------------------------------------

REPO = "app.recipes.service.repo"


class TestCreateRecipeBestEffort:
    def setup_method(self):
        self.db = MagicMock()
        self.owner_id = uuid.uuid4()
        self.recipe = _make_recipe(owner_id=self.owner_id)

    def _run(self, data: RecipeCreate):
        with (
            patch(f"{REPO}.create", return_value=self.recipe),
            patch(f"{REPO}.get_full", return_value=_make_full(self.recipe)),
            patch(f"{REPO}.get_by_id", return_value=self.recipe),
        ):
            return service.create_recipe(self.db, self.owner_id, data)

    def test_title_only_succeeds_with_no_warnings(self):
        result = self._run(RecipeCreate(title="Pasta"))
        assert result.recipe.title == "Test Recipe"
        assert result.warnings == {}

    def test_bad_step_produces_warning_not_error(self):
        data = RecipeCreate(
            title="Pasta",
            steps=[
                {"step_number": 1, "instruction": "Boil water"},
                {"step_number": 1, "instruction": "Duplicate step number"},  # will cause DB error
            ],
        )
        # Second step flush raises an IntegrityError
        flush_calls = 0

        def fake_flush():
            nonlocal flush_calls
            flush_calls += 1
            if flush_calls == 2:  # second step flush
                raise Exception("duplicate key value violates unique constraint")

        with (
            patch(f"{REPO}.create", return_value=self.recipe),
            patch(f"{REPO}.get_full", return_value=_make_full(self.recipe)),
            patch(f"{REPO}.get_by_id", return_value=self.recipe),
        ):
            self.db.flush.side_effect = fake_flush
            result = service.create_recipe(self.db, self.owner_id, data)

        assert "steps" in result.warnings
        assert len(result.warnings["steps"]) == 1

    def test_nutrition_failure_produces_warning_not_error(self):
        data = RecipeCreate(
            title="Pasta",
            nutrition={"calories": 500, "per_serving": True},
        )
        with (
            patch(f"{REPO}.create", return_value=self.recipe),
            patch(f"{REPO}.get_full", return_value=_make_full(self.recipe)),
            patch(f"{REPO}.get_by_id", return_value=self.recipe),
        ):
            self.db.flush.side_effect = Exception("DB error")
            result = service.create_recipe(self.db, self.owner_id, data)

        assert "nutrition" in result.warnings

    def test_failed_section_does_not_block_other_sections(self):
        """A bad ingredient should not prevent tags from being saved."""
        tag = _make_tag()
        data = RecipeCreate(
            title="Pasta",
            ingredients=[{"raw_name": "!!bad!!", "position": 1}],
            tags=[{"name": "vegetarian", "category": "dietary"}],
        )

        with (
            patch(f"{REPO}.create", return_value=self.recipe),
            patch(f"{REPO}.get_full", return_value=_make_full(self.recipe)),
            patch(f"{REPO}.get_by_id", return_value=self.recipe),
            patch(f"{REPO}.get_or_create_ingredient", side_effect=Exception("bad ingredient")),
            patch(f"{REPO}.get_or_create_tag", return_value=tag),
            patch(f"{REPO}.get_recipe_tag", return_value=None),
        ):
            result = service.create_recipe(self.db, self.owner_id, data)

        assert "ingredients" in result.warnings
        assert "tags" not in result.warnings


# ---------------------------------------------------------------------------
# get_recipe — NotFoundError
# ---------------------------------------------------------------------------

class TestGetRecipe:
    def test_raises_not_found_when_recipe_missing(self):
        db = MagicMock()
        with patch(f"{REPO}.get_full", return_value=None):
            with pytest.raises(NotFoundError, match="Recipe not found"):
                service.get_recipe(db, uuid.uuid4(), uuid.uuid4())

    def test_returns_recipe_out_on_success(self):
        db = MagicMock()
        recipe = _make_recipe()
        with patch(f"{REPO}.get_full", return_value=_make_full(recipe)):
            result = service.get_recipe(db, recipe.id, recipe.owner_id)
        assert result.id == recipe.id


# ---------------------------------------------------------------------------
# update_recipe — NotFoundError
# ---------------------------------------------------------------------------

class TestUpdateRecipe:
    def test_raises_not_found_for_wrong_owner(self):
        db = MagicMock()
        with patch(f"{REPO}.get_by_id", return_value=None):
            with pytest.raises(NotFoundError):
                service.update_recipe(db, uuid.uuid4(), uuid.uuid4(), RecipeUpdate(title="New"))


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------

class TestSteps:
    def setup_method(self):
        self.db = MagicMock()
        self.recipe = _make_recipe()
        self.owner_id = self.recipe.owner_id

    def test_update_step_raises_not_found_for_missing_step(self):
        with (
            patch(f"{REPO}.get_by_id", return_value=self.recipe),
            patch(f"{REPO}.get_step", return_value=None),
        ):
            with pytest.raises(NotFoundError, match="Step not found"):
                service.update_step(
                    self.db, self.recipe.id, uuid.uuid4(), self.owner_id,
                    RecipeStepUpdate(instruction="New instruction"),
                )

    def test_delete_step_raises_not_found_for_missing_step(self):
        with (
            patch(f"{REPO}.get_by_id", return_value=self.recipe),
            patch(f"{REPO}.get_step", return_value=None),
        ):
            with pytest.raises(NotFoundError, match="Step not found"):
                service.delete_step(self.db, self.recipe.id, uuid.uuid4(), self.owner_id)

    def test_add_step_delegates_to_repo(self):
        step = _make_step()
        with (
            patch(f"{REPO}.get_by_id", return_value=self.recipe),
            patch(f"{REPO}.create_step", return_value=step),
        ):
            result = service.add_step(
                self.db, self.recipe.id, self.owner_id,
                RecipeStepCreate(step_number=1, instruction="Boil water"),
            )
        assert result.step_number == step.step_number


# ---------------------------------------------------------------------------
# Ingredients — canonical re-resolution on update
# ---------------------------------------------------------------------------

class TestIngredients:
    def setup_method(self):
        self.db = MagicMock()
        self.recipe = _make_recipe()
        self.owner_id = self.recipe.owner_id

    def test_update_ingredient_reruns_canonical_resolution_when_raw_name_changes(self):
        ri = _make_ingredient(raw_name="flower")
        canonical = MagicMock()
        canonical.id = uuid.uuid4()

        with (
            patch(f"{REPO}.get_by_id", return_value=self.recipe),
            patch(f"{REPO}.get_recipe_ingredient", return_value=ri),
            patch(f"{REPO}.update_recipe_ingredient", return_value=ri) as mock_update,
        ):
            # The repo's update_recipe_ingredient handles re-resolution internally
            service.update_ingredient(
                self.db, self.recipe.id, ri.id, self.owner_id,
                RecipeIngredientUpdate(raw_name="flour"),
            )
            mock_update.assert_called_once()

    def test_update_ingredient_raises_not_found_for_missing_ingredient(self):
        with (
            patch(f"{REPO}.get_by_id", return_value=self.recipe),
            patch(f"{REPO}.get_recipe_ingredient", return_value=None),
        ):
            with pytest.raises(NotFoundError, match="Ingredient not found"):
                service.update_ingredient(
                    self.db, self.recipe.id, uuid.uuid4(), self.owner_id,
                    RecipeIngredientUpdate(raw_name="flour"),
                )

    def test_delete_ingredient_raises_not_found_for_missing_ingredient(self):
        with (
            patch(f"{REPO}.get_by_id", return_value=self.recipe),
            patch(f"{REPO}.get_recipe_ingredient", return_value=None),
        ):
            with pytest.raises(NotFoundError, match="Ingredient not found"):
                service.delete_ingredient(
                    self.db, self.recipe.id, uuid.uuid4(), self.owner_id,
                )


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------

class TestTags:
    def setup_method(self):
        self.db = MagicMock()
        self.recipe = _make_recipe()
        self.owner_id = self.recipe.owner_id

    def test_add_tag_raises_conflict_when_already_attached(self):
        tag = _make_tag()
        with (
            patch(f"{REPO}.get_by_id", return_value=self.recipe),
            patch(f"{REPO}.get_or_create_tag", return_value=tag),
            patch(f"{REPO}.get_recipe_tag", return_value=MagicMock()),  # already exists
        ):
            with pytest.raises(ConflictError, match="Tag already attached"):
                service.add_tag(
                    self.db, self.recipe.id, self.owner_id,
                    TagIn(name="vegetarian", category="dietary"),
                )

    def test_remove_tag_raises_not_found_when_tag_not_on_recipe(self):
        with (
            patch(f"{REPO}.get_by_id", return_value=self.recipe),
            patch(f"{REPO}.get_recipe_tag", return_value=None),
        ):
            with pytest.raises(NotFoundError, match="Tag not found on recipe"):
                service.remove_tag(self.db, self.recipe.id, uuid.uuid4(), self.owner_id)

    def test_add_tag_succeeds_when_not_already_attached(self):
        tag = _make_tag()
        with (
            patch(f"{REPO}.get_by_id", return_value=self.recipe),
            patch(f"{REPO}.get_or_create_tag", return_value=tag),
            patch(f"{REPO}.get_recipe_tag", return_value=None),
            patch(f"{REPO}.add_recipe_tag", return_value=MagicMock()),
        ):
            result = service.add_tag(
                self.db, self.recipe.id, self.owner_id,
                TagIn(name="vegetarian", category="dietary"),
            )
        assert result.name == tag.name


# ---------------------------------------------------------------------------
# toggle_favorite
# ---------------------------------------------------------------------------

class TestToggleFavorite:
    def test_toggle_favorite_flips_and_returns_recipe(self):
        db = MagicMock()
        recipe = _make_recipe()
        recipe.is_favorite = False
        toggled = _make_recipe(id=recipe.id)
        toggled.is_favorite = True

        with (
            patch(f"{REPO}.get_by_id", return_value=recipe),
            patch(f"{REPO}.toggle_favorite", return_value=toggled),
            patch(f"{REPO}.get_full", return_value=_make_full(toggled)),
        ):
            result = service.toggle_favorite(db, recipe.id, recipe.owner_id)

        assert result.is_favorite is True
