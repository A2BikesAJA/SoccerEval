from __future__ import annotations

"""Processing job schemas."""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ProcessingJobResponse(BaseModel):
    id: int
    game_id: int
    status: str
    progress_pct: float
    current_stage: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    model_config = {"from_attributes": True}
