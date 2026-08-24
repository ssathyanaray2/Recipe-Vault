import uuid
from typing import Optional

from pydantic import BaseModel

from app.models.source import SourceType


class SourceIn(BaseModel):
    source_type: SourceType
    name: str
    author: Optional[str] = None
    url: Optional[str] = None
    is_primary: bool = True


class SourceCreate(BaseModel):
    source_type: SourceType
    name: str
    author: Optional[str] = None
    url: Optional[str] = None
    is_primary: bool = True


class SourceUpdate(BaseModel):
    author: Optional[str] = None
    url: Optional[str] = None
    is_primary: Optional[bool] = None


class SourceOut(BaseModel):
    """id is recipe_sources.id — used for PATCH/DELETE on this recipe's source link."""
    id: uuid.UUID
    source_type: SourceType
    name: str
    author: Optional[str]
    url: Optional[str]
    is_primary: bool
