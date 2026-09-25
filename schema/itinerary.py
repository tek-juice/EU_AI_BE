from typing import List, Optional
from pydantic import BaseModel, Field

class TripRequirements(BaseModel):
    interests: List[str] = Field(default_factory=list)
    region: Optional[str] = None
    destination_preferences: List[str] = Field(
        default_factory=list
    )

    start_date: Optional[str] = None
    end_date: Optional[str] = None
    travelers: int = 1
    nights: int = 1
    budget_tier: Optional[str] = None