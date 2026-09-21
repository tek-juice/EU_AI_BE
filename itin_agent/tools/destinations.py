import json
from tools.config_tools.api_client import EuitineraryAPI
from nat.plugin_api import Builder, FunctionBaseConfig, FunctionInfo, register_function

class GetDestinationsConfig(FunctionBaseConfig, name="get_destinations"):
    """Fetch available destinations from the Everything Uganda API."""
    pass


@register_function(config_type=GetDestinationsConfig)
async def get_destinations(
    _config: GetDestinationsConfig,
    _builder: Builder,
):

    async def _get_destinations(_: str) -> str:

        api = EuitineraryAPI()

        response = api.get("/itinerary_data/destinations")

        destinations = response.get("destinations", [])

        return json.dumps(destinations)

    yield FunctionInfo.from_fn(
        _get_destinations,
        description=(
            "Returns all available destinations from the Everything Uganda "
            "API, including destination names, descriptions, regions, "
            "activities, and accommodations."
        ),
    )