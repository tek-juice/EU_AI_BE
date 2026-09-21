import json
from tools.config_tools.api_client import EuitineraryAPI
from nat.plugin_api import Builder, FunctionBaseConfig, FunctionInfo, register_function


class GetAccommodationsConfig(FunctionBaseConfig, name="get_accommodations"):
    """Fetch available accommodations from the Everything Uganda API."""
    pass


@register_function(config_type=GetAccommodationsConfig)
async def get_accommodations(
    _config: GetAccommodationsConfig,
    _builder: Builder,
):

    async def _get_accommodations(_: str) -> str:

        api = EuitineraryAPI()

        response = api.get("/itinerary_data/accommodations")

        accommodations = response.get("accommodations", [])

        return json.dumps(accommodations)

    yield FunctionInfo.from_fn(
        _get_accommodations,
        description=(
            "Returns all available accommodations from the Everything Uganda "
            "API, including accommodation names, types, destinations, ratings, "
            "room types, meal plans, and rates."
        ),
    )