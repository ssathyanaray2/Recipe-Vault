import uuid

from pydantic import BaseModel


class TagIn(BaseModel):
    name: str
    category: str  # dietary / meal_type / difficulty


class TagOut(BaseModel):
    id: uuid.UUID
    name: str
    category: str

    model_config = {"from_attributes": True}
