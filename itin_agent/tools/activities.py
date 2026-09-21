from tools.config_tools.api_client import EuitineraryAPI


api = EuitineraryAPI()


async def get_activities() -> list:
    """
    Get all available activities from the Everything Uganda API.
    """

    response = api.get(
        "/itinerary_data/activities"
    )

    return response