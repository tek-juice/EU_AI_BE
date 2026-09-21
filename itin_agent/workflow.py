"""
Everything Uganda - NAT Itinerary Builder Workflow

This workflow orchestrates the AI itinerary-building process.

The LLM is responsible for:
    - Understanding the customer's request
    - Selecting relevant information
    - Organizing the itinerary
    - Producing the final itinerary

Tools / backend services are responsible for:
    - Destinations
    - Activities
    - Accommodation
    - Business rules
"""

from typing import Any


class ItineraryWorkflow:
    """
    Main workflow for the Everything Uganda itinerary builder.
    """

    def __init__(
        self,
        llm: Any,
        tools: dict[str, Any],
    ):
        self.llm = llm
        self.tools = tools

    async def run(self, user_request: str) -> dict:
        """
        Process a customer request and generate an itinerary.
        """

        requirements = await self.extract_requirements(
            user_request
        )

        destinations = await self.get_destinations()

        activities = await self.get_activities()

        accommodations = await self.get_accommodations()

        itinerary = await self.build_itinerary(
            requirements=requirements,
            destinations=destinations,
            activities=activities,
            accommodations=accommodations,
    
        )

        validated_itinerary = await self.validate_itinerary(
            itinerary
        )

        return validated_itinerary
    
    async def extract_requirements(
        self,
        user_request: str,
    ) -> dict:
        """
        Extract structured requirements from the customer's
        natural-language request.

        NOTE:
        This is currently a placeholder. The LLM should eventually
        perform this extraction.
        """

        return {
            "raw_request": user_request,
            "travelers": None,
            "number_of_days": None,
            "number_of_nights": None,
            "start_date": None,
            "end_date": None,
            "budget": None,
            "currency": "USD",
            "interests": [],
            "accommodation_preference": None,
        }

    async def get_destinations(self) -> list:
        """
        Get available destinations from the Everything Uganda API.
        """

        tool = self.tools.get("get_destinations")

        if not tool:
            raise RuntimeError(
                "get_destinations tool is not registered"
            )

        return await tool()


    async def get_activities(self) -> list:
        """
        Get available activities from the Everything Uganda API.
        """

        tool = self.tools.get("get_activities")

        if not tool:
            raise RuntimeError(
                "get_activities tool is not registered"
            )

        return await tool()

    async def get_accommodations(self) -> list:
        """
        Get available accommodation from the Everything Uganda API.
        """

        tool = self.tools.get("get_accommodations")

        if not tool:
            raise RuntimeError(
                "get_accommodations tool is not registered"
            )

        return await tool()

    async def build_itinerary(
        self,
        requirements: dict,
        destinations: list,
        activities: list,
        accommodations: list,

    ) -> dict:
        """
        Use the LLM to organize the available data into a
        day-by-day itinerary.

        This will later call the configured LLM.
        """

        return {
            "requirements": requirements,
            "destinations": destinations,
            "activities": activities,
            "accommodations": accommodations,
            "days": [],
        }

    async def validate_itinerary(
        self,
        itinerary: dict,
    ) -> dict:
        """
        Validate the generated itinerary against business rules.
        """

        tool = self.tools.get(
            "validate_itinerary"
        )

        if not tool:
            raise RuntimeError(
                "validate_itinerary tool is not registered"
            )

        return await tool(itinerary)