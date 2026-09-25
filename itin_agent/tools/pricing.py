# from tools.config_tools.api_client import EuitineraryAPI


# api = EuitineraryAPI()


# async def calculate_itinerary_price(
#     requirements: dict,
#     destinations: list,
#     activities: list,
#     accommodations: list,
# ) -> dict:

#     payload = {
#         "travelers": requirements.get("travelers"),
#         "number_of_days": requirements.get("number_of_days"),
#         "number_of_nights": requirements.get("number_of_nights"),
#         "activities": [
#             activity["id"]
#             for activity in activities
#         ],
#         "accommodations": [
#             accommodation["id"]
#             for accommodation in accommodations
#         ]
#     }

#     return api.post(
#         "/itineraries/calculate-price",
#         json=payload
#     )