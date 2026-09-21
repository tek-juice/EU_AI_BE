from pydantic import BaseModel
from typing import Optional


class DestinationOutput(BaseModel):
    id: str
    name: str


class AccommodationOutput(BaseModel):
    id: str
    name: str
    room_type: Optional[str] = None
    meal_plan: Optional[str] = None


class ActivityOutput(BaseModel):
    id: str
    name: str
    activity_type: Optional[str] = None
    duration_minutes: Optional[int] = None
    start_time: Optional[str] = None
    notes: Optional[str] = None


class ItineraryDayOutput(BaseModel):
    day_number: int
    date: Optional[str] = None
    destination: DestinationOutput
    accommodation: Optional[AccommodationOutput] = None
    activities: list[ActivityOutput] = []
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