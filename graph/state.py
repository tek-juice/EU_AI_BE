# itin_agent/state.py

from typing import Any, Dict, List, Optional, TypedDict


class ItineraryState(TypedDict, total=False):
    # User/session information
    user_id: str
    conversation_id: Optional[str]
    itinerary_id: Optional[str]

    # Original user request
    user_message: str

    # Extracted trip requirements
    destination_preferences: List[str]
    interests: List[str]
    region: Optional[str]

    start_date: Optional[str]
    end_date: Optional[str]

    travelers: int
    nights: int

    budget_tier: Optional[str]

    # Retrieved information
    destinations: List[Dict[str, Any]]
    activities: List[Dict[str, Any]]
    accommodations: List[Dict[str, Any]]

    # Agent selections
    selected_destinations: List[Dict[str, Any]]
    selected_activities: List[Dict[str, Any]]
    selected_accommodation: Optional[Dict[str, Any]]

    # Pricing
    price: Optional[Dict[str, Any]]

    # Generated itinerary
    itinerary: Optional[Dict[str, Any]]

    # Conversation
    messages: List[Dict[str, str]]

    # Control flow
    next_step: Optional[str]

    # Errors
    error: Optional[str]