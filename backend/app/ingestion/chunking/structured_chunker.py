"""
Structured chunking strategy — three chunk types per recipe:
  meta        : title, cuisine, difficulty, servings, time, description, tags, notes
  ingredients : one or more chunks if ingredient list is large
  steps       : one or more chunks if instruction list is large

Every chunk is prefixed with the recipe title so it makes sense in isolation
when retrieved without context. Every chunk carries recipe_id so search results
can be deduplicated and mapped back to the parent recipe.

Token estimation: len(text) // 4  (4 chars ≈ 1 token for English text).
"""
from app.core.config import settings
from app.ingestion.chunking.base import Chunk
from app.models.ingredient import RecipeIngredient
from app.models.recipe import Recipe, RecipeStep
from app.models.tag import Tag

_CHARS_PER_TOKEN = 4


def _estimate_tokens(text: str) -> int:
    return len(text) // _CHARS_PER_TOKEN


def _split_lines(lines: list[str], max_tokens: int) -> list[list[str]]:
    """
    Greedily splits a list of text lines into groups that each fit within
    max_tokens. A single line that exceeds the limit becomes its own group.
    """
    groups: list[list[str]] = []
    current: list[str] = []
    current_tokens = 0

    for line in lines:
        line_tokens = _estimate_tokens(line)
        if current and current_tokens + line_tokens > max_tokens:
            groups.append(current)
            current = [line]
            current_tokens = line_tokens
        else:
            current.append(line)
            current_tokens += line_tokens

    if current:
        groups.append(current)

    return groups or [[]]


class StructuredRecipeChunker:
    """
    Produces 3–N chunks per recipe depending on how large the ingredient
    and step lists are.
    """

    def __init__(self, max_tokens: int | None = None) -> None:
        self._max_tokens = max_tokens or settings.CHUNK_MAX_TOKENS

    def chunk(
        self,
        recipe: Recipe,
        steps: list[RecipeStep],
        ingredients: list[RecipeIngredient],
        tags: list[Tag],
    ) -> list[Chunk]:
        recipe_id = str(recipe.id)
        chunks: list[Chunk] = []

        chunks.append(self._meta_chunk(recipe, tags, recipe_id))
        chunks.extend(self._ingredient_chunks(recipe, ingredients, recipe_id))
        chunks.extend(self._step_chunks(recipe, steps, recipe_id))

        return chunks

    # ------------------------------------------------------------------
    # Meta chunk
    # ------------------------------------------------------------------

    def _meta_chunk(self, recipe: Recipe, tags: list[Tag], recipe_id: str) -> Chunk:
        lines: list[str] = [f"Recipe: {recipe.title}"]

        meta_parts = []
        if recipe.cuisine:
            meta_parts.append(f"Cuisine: {recipe.cuisine}")
        if recipe.difficulty:
            meta_parts.append(f"Difficulty: {recipe.difficulty.value}")
        if recipe.servings:
            meta_parts.append(f"Servings: {recipe.servings}")
        if recipe.total_time_minutes:
            meta_parts.append(f"Total time: {recipe.total_time_minutes} minutes")
        if meta_parts:
            lines.append(" | ".join(meta_parts))

        if tags:
            lines.append("Tags: " + ", ".join(t.name for t in tags))

        if recipe.description:
            lines.append("")
            lines.append(recipe.description)

        if recipe.notes:
            lines.append("")
            lines.append(f"Notes: {recipe.notes}")

        return Chunk(
            point_id=f"{recipe_id}:meta",
            text="\n".join(lines),
            chunk_type="meta",
            recipe_id=recipe_id,
        )

    # ------------------------------------------------------------------
    # Ingredient chunks
    # ------------------------------------------------------------------

    def _ingredient_chunks(
        self, recipe: Recipe, ingredients: list[RecipeIngredient], recipe_id: str
    ) -> list[Chunk]:
        if not ingredients:
            return []

        header = f"Recipe: {recipe.title} — Ingredients"
        lines = [self._format_ingredient(ing) for ing in ingredients]
        groups = _split_lines(lines, self._max_tokens)

        return [
            Chunk(
                point_id=f"{recipe_id}:ingredients:{i}",
                text=header + "\n" + "\n".join(group),
                chunk_type="ingredients",
                recipe_id=recipe_id,
                )
            for i, group in enumerate(groups)
        ]

    @staticmethod
    def _format_ingredient(ing: RecipeIngredient) -> str:
        parts = []
        if ing.quantity:
            parts.append(str(ing.quantity))
        if ing.unit:
            parts.append(ing.unit)
        parts.append(ing.raw_name)
        if ing.prep_note:
            parts.append(f"({ing.prep_note})")
        return "- " + " ".join(parts)

    # ------------------------------------------------------------------
    # Step chunks
    # ------------------------------------------------------------------

    def _step_chunks(
        self, recipe: Recipe, steps: list[RecipeStep], recipe_id: str
    ) -> list[Chunk]:
        if not steps:
            return []

        header = f"Recipe: {recipe.title} — Instructions"
        lines = [f"{s.step_number}. {s.instruction}" for s in steps]
        groups = _split_lines(lines, self._max_tokens)

        return [
            Chunk(
                point_id=f"{recipe_id}:steps:{i}",
                text=header + "\n" + "\n".join(group),
                chunk_type="steps",
                recipe_id=recipe_id,
                )
            for i, group in enumerate(groups)
        ]
