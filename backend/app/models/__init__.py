# Import all models here so Base.metadata is fully populated when alembic runs.
from app.models.chat import ChatMessage, ChatSession
from app.models.cook_log import CookLog
from app.models.embedding import RecipeEmbedding
from app.models.ingredient import Ingredient, RecipeIngredient
from app.models.memory import UserMemory
from app.models.nutrition import NutritionFacts
from app.models.recipe import DifficultyLevel, Recipe, RecipeImage, RecipeStep
from app.models.source import RecipeSource, Source, SourceType
from app.models.tag import RecipeTag, Tag
from app.models.user import User

__all__ = [
    "User",
    "Recipe",
    "RecipeStep",
    "RecipeImage",
    "DifficultyLevel",
    "Ingredient",
    "RecipeIngredient",
    "Tag",
    "RecipeTag",
    "Source",
    "RecipeSource",
    "SourceType",
    "NutritionFacts",
    "CookLog",
    "RecipeEmbedding",
    "UserMemory",
    "ChatSession",
    "ChatMessage",
]
