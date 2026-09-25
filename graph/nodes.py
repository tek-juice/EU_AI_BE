# itin_agent/nodes.py

from langchain_core.messages import HumanMessage, SystemMessage
from tools.itinerary_tools import get_accommodations, get_activities, get_destinations
from schema.itinerary import TripRequirements
from graph.state import ItineraryState


def extract_requirements(
    state: ItineraryState,
    llm,
) -> ItineraryState:

    user_message = state.get("user_message", "")

    structured_llm = llm.with_structured_output(
        TripRequirements
    )

    requirements = structured_llm.invoke([
        SystemMessage(
            content="""
You extract travel requirements for the Everything Uganda
itinerary builder.

Never invent information.

If the user does not specify something, leave it empty or null.
"""
        ),
        HumanMessage(content=user_message),
    ])

    return {
        **state,

        "interests": requirements.interests,
        "region": requirements.region,

        "destination_preferences": (
            requirements.destination_preferences
        ),

        "start_date": requirements.start_date,
        "end_date": requirements.end_date,

        "travelers": requirements.travelers,
        "nights": requirements.nights,

        "budget_tier": requirements.budget_tier,
    }

def search_destinations(
    state: ItineraryState,
) -> ItineraryState:

    result = get_destinations.invoke({
        "region": state.get("region"),
        "interests": state.get("interests", []),
        "max_results": 10,
    })

    return {
        **state,
        "destinations": result.get("destinations", result),
    }

def search_activities(
    state: ItineraryState,
) -> ItineraryState:

    result = get_activities.invoke({})

    return {
        **state,
        "activities": result.get("activities", result),
    }


def search_accommodations(
    state: ItineraryState,
) -> ItineraryState:

    result = get_accommodations.invoke({
        "budget_tier": state.get("budget_tier"),
    })

    return {
        **state,
        "accommodations": result.get(
            "accommodations",
            result
        ),
    }


from langchain_core.messages import HumanMessage, SystemMessage


def select_itinerary(
    state: ItineraryState,
    llm,
) -> ItineraryState:

    destinations = state.get("destinations", [])
    activities = state.get("activities", [])
    accommodations = state.get("accommodations", [])

    prompt = f"""
Create an itinerary selection using ONLY the data provided.

Traveler requirements:

Interests:
{state.get("interests", [])}

Preferred destinations:
{state.get("destination_preferences", [])}

Region:
{state.get("region")}

Travelers:
{state.get("travelers", 1)}

Nights:
{state.get("nights", 1)}

Budget tier:
{state.get("budget_tier")}

AVAILABLE DESTINATIONS:
{destinations}

AVAILABLE ACTIVITIES:
{activities}

AVAILABLE ACCOMMODATIONS:
{accommodations}

Rules:

1. Never invent a destination.
2. Never invent an activity.
3. Never invent an accommodation.
4. Only select items from the supplied data.
5. Activities must belong to selected destinations.
6. Accommodations must belong to selected destinations.
"""

    response = llm.invoke([
        SystemMessage(
            content="You are the Everything Uganda itinerary planner."
        ),
        HumanMessage(content=prompt),
    ])

    return {
        **state,
        "itinerary": response.content,
    }


def generate_itinerary(
    state: ItineraryState,
    llm,
) -> ItineraryState:

    prompt = f"""
Create the final Uganda travel itinerary.

Traveler requirements:
- Travelers: {state.get("travelers")}
- Nights: {state.get("nights")}
- Start date: {state.get("start_date")}
- End date: {state.get("end_date")}

Selected destinations:
{state.get("selected_destinations", [])}

Selected activities:
{state.get("selected_activities", [])}

Selected accommodation:
{state.get("selected_accommodation")}

Price:
{state.get("price")}

Create a clear day-by-day itinerary.

Do not introduce destinations, activities,
accommodations, or prices that are not present
in the supplied data.
"""

    response = llm.invoke([
        SystemMessage(
            content="""
You are the Everything Uganda itinerary generator.
Generate a practical, readable travel itinerary.
"""
        ),
        HumanMessage(content=prompt),
    ])

    return {
        **state,
        "itinerary": response.content,
    }


def generate_itinerary(
    state: ItineraryState,
    llm,
) -> ItineraryState:

    prompt = f"""
Create the final Uganda travel itinerary.

Traveler requirements:
- Travelers: {state.get("travelers")}
- Nights: {state.get("nights")}
- Start date: {state.get("start_date")}
- End date: {state.get("end_date")}

Selected destinations:
{state.get("selected_destinations", [])}

Selected activities:
{state.get("selected_activities", [])}

Selected accommodation:
{state.get("selected_accommodation")}

Price:
{state.get("price")}

Create a clear day-by-day itinerary.

Do not introduce destinations, activities,
accommodations, or prices that are not present
in the supplied data.
"""

    response = llm.invoke([
        SystemMessage(
            content="""
You are the Everything Uganda itinerary generator.
Generate a practical, readable travel itinerary.
"""
        ),
        HumanMessage(content=prompt),
    ])

    return {
        **state,
        "itinerary": response.content,
    }