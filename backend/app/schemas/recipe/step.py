import uuid
from typing import Optional

from pydantic import BaseModel, Field


class RecipeStepIn(BaseModel):
    step_number: int = Field(ge=1)
    instruction: str
    timer_seconds: Optional[int] = Field(default=None, ge=1)


class RecipeStepCreate(BaseModel):
    step_number: int = Field(ge=1)
    instruction: str
    timer_seconds: Optional[int] = Field(default=None, ge=1)


class RecipeStepUpdate(BaseModel):
    step_number: Optional[int] = Field(default=None, ge=1)
    instruction: Optional[str] = None
    timer_seconds: Optional[int] = Field(default=None, ge=1)


class StepReorderItem(BaseModel):
    step_id: uuid.UUID
    step_number: int = Field(ge=1)


class RecipeStepOut(BaseModel):
    id: uuid.UUID
    step_number: int
    instruction: str
    timer_seconds: Optional[int]

    model_config = {"from_attributes": True}
