"""
Single-chunk strategy — one vector per recipe combining all fields into
structured plain text. Human-readable format works well with embedding models.
"""
from app.ingestion.chunking.base import Chunk
from app.models.ingredient import RecipeIngredient
from app.models.recipe import Recipe, RecipeStep
from app.models.tag import Tag


def _build_embedding_text(
    recipe: Recipe,
    steps: list[RecipeStep],
    ingredients: list[RecipeIngredient],
    tags: list[Tag],
) -> str:
    lines: list[str] = []

    lines.append(f"Recipe: {recipe.title}")

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

    if recipe.description:
        lines.append("")
        lines.append(recipe.description)

    if tags:
        lines.append("")
        lines.append("Tags: " + ", ".join(t.name for t in tags))

    if ingredients:
        lines.append("")
        lines.append("Ingredients:")
        for ing in ingredients:
            parts = []
            if ing.quantity:
                parts.append(str(ing.quantity))
            if ing.unit:
                parts.append(ing.unit)
            parts.append(ing.raw_name)
            if ing.prep_note:
                parts.append(f"({ing.prep_note})")
            lines.append("- " + " ".join(parts))

    if steps:
        lines.append("")
        lines.append("Instructions:")
        for step in steps:
            lines.append(f"{step.step_number}. {step.instruction}")

    if recipe.notes:
        lines.append("")
        lines.append(f"Notes: {recipe.notes}")

    return "\n".join(lines)


class SingleRecipeChunker:
    """Produces exactly one chunk per recipe."""

    def chunk(
        self,
        recipe: Recipe,
        steps: list[RecipeStep],
        ingredients: list[RecipeIngredient],
        tags: list[Tag],
    ) -> list[Chunk]:
        recipe_id = str(recipe.id)
        return [
            Chunk(
                point_id=f"{recipe_id}:full",
                text=_build_embedding_text(recipe, steps, ingredients, tags),
                chunk_type="full",
                recipe_id=recipe_id,
            )
        ]
