from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class UserIntent(BaseModel):
    """
    Structured representation of what the user wants
    the itinerary agent to do.
    """

    intent: Literal[
        "create_itinerary",
        "modify_itinerary",
        "add_activity",
        "remove_activity",
        "change_destination",
        "change_accommodation",
        "change_dates",
        "change_guests",
        "change_budget",
        "show_itinerary",
        "calculate_price",
        "ask_question",
        "confirm_itinerary",
        "cancel_itinerary"
    ]

    changes: Dict[str, Any] = Field(
        default_factory=dict,
        description="Specific changes requested by the user."
    )

    missing_information: List[str] = Field(
        default_factory=list,
        description="Information still required before the agent can continue."
    )

    requires_clarification: bool = Field(
        default=False,
        description="Whether the agent needs to ask the user a question."
    )

    clarification_question: Optional[str] = Field(
        default=None,
        description="Question to ask the user if clarification is required."
    )