# itin_agent/graph.py

from langgraph.graph import StateGraph, START, END

from graph.state import ItineraryState
from graph.nodes import (
    extract_requirements,
    search_destinations,
    search_activities,
    search_accommodations,
    select_itinerary,
    # calculate_itinerary_price,
    generate_itinerary,
)


def build_graph(llm):

    graph = StateGraph(ItineraryState)

    # Nodes
    graph.add_node(
        "extract_requirements",
        lambda state: extract_requirements(state, llm),
    )

    graph.add_node(
        "search_destinations",
        search_destinations,
    )

    graph.add_node(
        "search_activities",
        search_activities,
    )

    graph.add_node(
        "search_accommodations",
        search_accommodations,
    )

    graph.add_node(
        "select_itinerary",
        lambda state: select_itinerary(state, llm),
    )

    # graph.add_node(
    #     "calculate_price",
    #     calculate_itinerary_price,
    # )

    graph.add_node(
        "generate_itinerary",
        lambda state: generate_itinerary(state, llm),
    )

    # Flow
    graph.add_edge(
        START,
        "extract_requirements",
    )

    graph.add_edge(
        "extract_requirements",
        "search_destinations",
    )

    graph.add_edge(
        "search_destinations",
        "search_activities",
    )

    graph.add_edge(
        "search_activities",
        "search_accommodations",
    )

    graph.add_edge(
        "search_accommodations",
        "select_itinerary",
    )

    graph.add_edge(
        "select_itinerary",
        "calculate_price",
    )

    graph.add_edge(
        "calculate_price",
        "generate_itinerary",
    )

    graph.add_edge(
        "generate_itinerary",
        END,
    )

    return graph.compile()