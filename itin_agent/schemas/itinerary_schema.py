"""
Schemas for the Everything Uganda itinerary builder.

Backwards compatible with the original file, with these additions:
  - names are optional on output models (the LLM only has to choose IDs;
    pipeline.normalize_itinerary fills names from the catalog)
  - AccommodationOutput / ActivityOutput carry a rate_id, and
    AccommodationOutput carries `rooms`, so pricing can be added later
    without a schema change
  - TripRequirements: what the pipeline extracts from the customer request
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


def parse_iso_date(value: Optional[str]) -> Optional[date]:
    """Parse YYYY-MM-DD; return None for missing or malformed values."""
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None

class DestinationOutput(BaseModel):
    id: str
    name: str = ""


class AccommodationOutput(BaseModel):
    id: str
    name: str = ""
    rate_id: Optional[str] = None
    room_type: Optional[str] = None
    meal_plan: Optional[str] = None
    rooms: Optional[int] = None


class ActivityOutput(BaseModel):
    id: str
    name: str = ""
    rate_id: Optional[str] = None
    activity_type: Optional[str] = None
    duration_minutes: Optional[int] = None
    start_time: Optional[str] = None
    notes: Optional[str] = None


class ItineraryDayOutput(BaseModel):
    day_number: int
    date: Optional[str] = None
    destination: DestinationOutput
    accommodation: Optional[AccommodationOutput] = None
    activities: list[ActivityOutput] = Field(default_factory=list)
    notes: Optional[str] = None


class TripOutput(BaseModel):
    number_of_days: int
    number_of_nights: int
    travelers: int
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    currency: str = "USD"


class ItineraryOutput(BaseModel):
    trip: TripOutput
    days: list[ItineraryDayOutput]


class TripRequirements(BaseModel):
    travelers: Optional[int] = None
    number_of_days: Optional[int] = None
    number_of_nights: Optional[int] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    budget: Optional[float] = None
    currency: str = "USD"
    interests: list[str] = Field(default_factory=list)
    destination_preferences: list[str] = Field(default_factory=list)
    accommodation_preference: Optional[str] = None

    def normalized(self) -> "TripRequirements":
        """Derive days/nights from each other (or from dates) when possible."""
        data = self.model_copy(deep=True)
        start = parse_iso_date(data.start_date)
        end = parse_iso_date(data.end_date)

        if data.number_of_days is None and start and end and end >= start:
            data.number_of_days = (end - start).days + 1
        if data.number_of_days is None and data.number_of_nights is not None:
            data.number_of_days = data.number_of_nights + 1
        if data.number_of_nights is None and data.number_of_days is not None:
            data.number_of_nights = max(data.number_of_days - 1, 0)
        return data

    def missing_fields(self) -> list[str]:
        """Fields we cannot build an itinerary without."""
        missing = []
        if not self.travelers or self.travelers < 1:
            missing.append("travelers")
        if not self.number_of_days or self.number_of_days < 1:
            missing.append("number_of_days")
        return missing

    def merged_with(self, newer: "TripRequirements") -> "TripRequirements":
        """
        Combine requirements from an earlier turn with a newer extraction.
        Newly stated values win; lists are unioned; unstated fields are kept.
        """
        data = self.model_dump()
        for key in newer.model_fields_set:
            value = getattr(newer, key)
            if value is None or value == "":
                continue
            if isinstance(value, list):
                if not value:
                    continue
                data[key] = list(dict.fromkeys([*data.get(key, []), *value]))
            else:
                data[key] = value

        # A changed day count invalidates a previously derived night count
        # (and vice versa), so let normalized() re-derive it.
        stated = {
            key
            for key in newer.model_fields_set
            if getattr(newer, key) not in (None, "", [])
        }
        if "number_of_days" in stated and "number_of_nights" not in stated:
            data["number_of_nights"] = None
        if "number_of_nights" in stated and "number_of_days" not in stated:
            data["number_of_days"] = None
        return TripRequirements(**data)
