from tools.config_tools.api_client import EuitineraryAPI


api = EuitineraryAPI()


async def get_accommodations() -> list:
    """
    Get all available accommodations from the Everything Uganda API.
    """

    response = api.get(
        "/itinerary_data/accommodations"
    )

    return response