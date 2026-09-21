
import json
from tools.config_tools.api_client import EuitineraryAPI
from nat.plugin_api import Builder, FunctionBaseConfig, FunctionInfo, register_function


class GetActivitiesConfig(FunctionBaseConfig, name="get_activities"):
    """Fetch available activities from the Everything Uganda API."""
    pass


@register_function(config_type=GetActivitiesConfig)
async def get_activities(
    _config: GetActivitiesConfig,
    _builder: Builder,
):

    async def _get_activities(_: str) -> str:

        api = EuitineraryAPI()

        response = api.get("/itinerary_data/activities")

        activities = response.get("activities", [])

        return json.dumps(activities)

    yield FunctionInfo.from_fn(
        _get_activities,
        description=(
            "Returns all available activities from the Everything Uganda "
            "API, including activity names, types, descriptions, destination "
            "IDs, destinations, images, and rates."
        ),
    )