import uuid

from pydantic import BaseModel


class RecipeImageIn(BaseModel):
    url: str
    is_primary: bool = False
    position: int = 0


class RecipeImageOut(BaseModel):
    id: uuid.UUID
    url: str
    is_primary: bool
    position: int

    model_config = {"from_attributes": True}
