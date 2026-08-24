import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CookLogCreate(BaseModel):
    cooked_at: Optional[datetime] = None
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    notes: Optional[str] = None


class CookLogOut(BaseModel):
    id: uuid.UUID
    cooked_at: datetime
    rating: Optional[int]
    notes: Optional[str]

    model_config = {"from_attributes": True}
