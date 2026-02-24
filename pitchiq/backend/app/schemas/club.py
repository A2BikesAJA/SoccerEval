from __future__ import annotations

"""Club schemas."""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ClubCreate(BaseModel):
    name: str
    logo_url: Optional[str] = None


class ClubResponse(BaseModel):
    id: int
    name: str
    logo_url: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
