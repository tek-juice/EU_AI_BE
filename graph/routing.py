def route_after_requirements(state):
    """
    Decide whether enough information exists to search
    for destinations.
    """

    if state.get("error"):
        return "error"

    return "search_destinations"