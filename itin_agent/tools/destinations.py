from tools.config_tools.api_client import EuitineraryAPI

api = EuitineraryAPI()

async def get_destinations() -> list:
    """
    Get all available destinations from the Everything Uganda API.
    """

    response = api.get(
        "/itinerary_data/destinations"
    )

    return response