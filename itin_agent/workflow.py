"""
Everything Uganda - NAT Itinerary Builder Workflow

This workflow orchestrates the AI itinerary-building process.

The LLM is responsible for:
    - Understanding the customer's request
    - Deciding which tools are required
    - Combining tool results
    - Producing the itinerary

The database/API is responsible for:
    - Destinations
    - Activities
    - Accommodation
    - Transport
    - Prices
    - Business rules
"""

import inspect
import json
from typing import Any


class ItineraryWorkflow:
    """
    Main workflow for the Everything Uganda itinerary builder.
    """

    def __init__(self, llm: Any, tools: dict[str, Any]):
        self.llm = llm
        self.tools = tools

    async def run(self, user_request: str) -> dict:
        """
        Process a customer request and generate an itinerary.
        """

        requirements = await self.extract_requirements(
            user_request
        )

        destinations = await self.search_destinations(
            requirements
        )

        activities = await self.search_activities(
            requirements,
            destinations
        )

        accommodations = await self.search_accommodations(
            requirements,
            destinations
        )


        pricing = await self.calculate_price(
            requirements=requirements,
            destinations=destinations,
            activities=activities,
            accommodations=accommodations,
 
        )

        itinerary = await self.build_itinerary(
            requirements=requirements,
            destinations=destinations,
            activities=activities,
            accommodations=accommodations,
            pricing=pricing
        )

        validated_itinerary = await self.validate_itinerary(
            itinerary
        )

        return validated_itinerary

    async def extract_requirements(
        self,
        user_request: str
    ) -> dict:

        """
        Extract structured requirements from the customer's
        natural-language request.
        """

        schema = {
            "title": "ItineraryRequirements",
            "type": "object",
            "properties": {
                "travelers": {"type": ["integer", "null"]},
                "number_of_days": {"type": ["integer", "null"]},
                "number_of_nights": {"type": ["integer", "null"]},
                "start_date": {"type": ["string", "null"]},
                "end_date": {"type": ["string", "null"]},
                "budget": {"type": ["number", "null"]},
                "currency": {"type": "string"},
                "interests": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "accommodation_preference": {"type": ["string", "null"]},
            },
            "required": [
                "travelers",
                "number_of_days",
                "number_of_nights",
                "start_date",
                "end_date",
                "budget",
                "currency",
                "interests",
                "accommodation_preference",
            ],
        }

        prompt = (
            "Extract itinerary requirements from this customer request. "
            "Return only JSON matching this schema: "
            f"{json.dumps(schema, separators=(',', ':'))}\n\n"
            f"Customer request: {user_request}"
        )

        llm = self.llm
        if hasattr(llm, "with_structured_output"):
            llm = llm.with_structured_output(schema)

        if hasattr(llm, "ainvoke"):
            result = await llm.ainvoke(prompt)
        elif hasattr(llm, "invoke"):
            result = llm.invoke(prompt)
        else:
            result = llm(prompt)

        if inspect.isawaitable(result):
            result = await result

        if not isinstance(result, dict):
            content = getattr(result, "content", result)
            if isinstance(content, str):
                content = content.strip()
                if content.startswith("```"):
                    content = content.strip("`")
                    content = content.removeprefix("json").strip()
                result = json.loads(content)
            else:
                result = dict(content)

        requirements = {
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
        requirements.update({
            key: result.get(key, requirements[key])
            for key in requirements
            if key != "raw_request"
        })
        requirements["currency"] = (
            requirements.get("currency") or "USD"
        ).upper()
        requirements["interests"] = requirements.get("interests") or []

        return requirements

    async def search_destinations(
        self,
        requirements: dict
    ) -> list:

        """
        Find destinations matching the customer's requirements.
        """

        tool = self.tools.get("search_destinations")

        if not tool:
            raise RuntimeError(
                "search_destinations tool is not registered"
            )

        return await tool(requirements)

    async def search_activities(
        self,
        requirements: dict,
        destinations: list
    ) -> list:

        """
        Find activities available at the selected destinations.
        """

        tool = self.tools.get("search_activities")

        if not tool:
            raise RuntimeError(
                "search_activities tool is not registered"
            )

        return await tool(
            requirements,
            destinations
        )

    async def search_accommodations(
        self,
        requirements: dict,
        destinations: list
    ) -> list:

        """
        Find accommodation options for the selected destinations.
        """

        tool = self.tools.get("search_accommodations")

        if not tool:
            raise RuntimeError(
                "search_accommodations tool is not registered"
            )

        return await tool(
            requirements,
            destinations
        )

    async def search_transport(
        self,
        requirements: dict,
        destinations: list
    ) -> list:

        """
        Find appropriate transport options.
        """

        tool = self.tools.get("search_transport")

        if not tool:
            raise RuntimeError(
                "search_transport tool is not registered"
            )

        return await tool(
            requirements,
            destinations
        )

    async def calculate_price(
        self,
        requirements: dict,
        destinations: list,
        activities: list,
        accommodations: list,
        transport: list
    ) -> dict:

        """
        Calculate the itinerary price using backend pricing
        logic.

        The LLM must NOT calculate authoritative prices.
        """

        tool = self.tools.get("calculate_itinerary_price")

        if not tool:
            raise RuntimeError(
                "calculate_itinerary_price tool is not registered"
            )

        return await tool(
            requirements=requirements,
            destinations=destinations,
            activities=activities,
            accommodations=accommodations,
            transport=transport
        )

    async def build_itinerary(
        self,
        requirements: dict,
        destinations: list,
        activities: list,
        accommodations: list,
        transport: list,
        pricing: dict
    ) -> dict:

        """
        Use the LLM to organize the available data into a
        day-by-day itinerary.
        """

        # TODO:
        # This will use the NAT LLM/workflow implementation.

        return {
            "requirements": requirements,
            "destinations": destinations,
            "activities": activities,
            "accommodations": accommodations,
            "transport": transport,
            "pricing": pricing,
            "days": []
        }

    async def validate_itinerary(
        self,
        itinerary: dict
    ) -> dict:

        """
        Validate the generated itinerary against business rules.
        """

        tool = self.tools.get("validate_itinerary")

        if not tool:
            raise RuntimeError(
                "validate_itinerary tool is not registered"
            )

        return await tool(itinerary)
