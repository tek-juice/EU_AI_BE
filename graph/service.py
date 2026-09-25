from graph.graph import build_graph

def run_itinerary_agent(
    llm,
    user_id: str,
    message: str,
    conversation_id: str | None = None,
):
    graph = build_graph(llm)

    initial_state = {
        "user_id": user_id,
        "conversation_id": conversation_id,
        "user_message": message,
        "messages": [],
    }

    result = graph.invoke(initial_state)

    return result