"""
In-memory view of the Everything Uganda catalog.

The validator and pipeline work against this object rather than the raw API,
so they are easy to test and never touch the network themselves.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any, Iterable, Optional


class Catalog:
    """Destinations, activities and accommodations, indexed by id."""

    def __init__(
        self,
        destinations: Iterable[dict],
        activities: Iterable[dict],
        accommodations: Iterable[dict],
    ):
        self.destinations: dict[str, dict] = {
            str(d["id"]): d for d in destinations
        }
        self.activities: dict[str, dict] = {
            str(a["id"]): a for a in activities
        }
        self.accommodations: dict[str, dict] = {
            str(a["id"]): a for a in accommodations
        }

        self.activities_by_destination: dict[str, list[dict]] = defaultdict(list)
        for activity in self.activities.values():
            self.activities_by_destination[
                str(activity.get("destination_id"))
            ].append(activity)

        self.accommodations_by_destination: dict[str, list[dict]] = defaultdict(list)
        for accommodation in self.accommodations.values():
            self.accommodations_by_destination[
                str(accommodation.get("destination_id"))
            ].append(accommodation)

        # rate_id -> (accommodation_id, rate)
        self.rate_index: dict[str, tuple[str, dict]] = {}
        for accommodation_id, accommodation in self.accommodations.items():
            for rate in accommodation.get("rates") or []:
                self.rate_index[str(rate["id"])] = (accommodation_id, rate)

    @classmethod
    async def load(cls, api: Optional[Any] = None) -> "Catalog":
        """
        Fetch the catalog from the Everything Uganda API.

        EuitineraryAPI uses blocking `requests`, so each call runs in a
        worker thread and the three fetches run concurrently.
        """
        if api is None:
            from itin_agent.tools.config_tools.api_client import EuitineraryAPI

            api = EuitineraryAPI()

        destinations, activities, accommodations = await asyncio.gather(
            asyncio.to_thread(api.get, "/itinerary_data/destinations"),
            asyncio.to_thread(api.get, "/itinerary_data/activities"),
            asyncio.to_thread(api.get, "/itinerary_data/accommodations"),
        )
        return cls(
            destinations.get("destinations", []),
            activities.get("activities", []),
            accommodations.get("accommodations", []),
        )


class TravelTimes:
    """
    Drive/transfer minutes between destinations (symmetric).

    There is no data source for this yet. Until you add a travel-time table,
    an empty TravelTimes makes the validator emit TRAVEL_TIME_UNKNOWN
    warnings instead of enforcing transfer limits.
    """

    def __init__(self, minutes: Optional[dict[tuple[str, str], int]] = None):
        self._minutes: dict[frozenset, int] = {}
        for (a, b), value in (minutes or {}).items():
            self.set(a, b, value)

    def set(self, a: str, b: str, minutes: int) -> None:
        self._minutes[frozenset((str(a), str(b)))] = int(minutes)

    def get(self, a: str, b: str) -> Optional[int]:
        if str(a) == str(b):
            return 0
        return self._minutes.get(frozenset((str(a), str(b))))

    @classmethod
    def from_rows(cls, rows: Iterable[dict]) -> "TravelTimes":
        """rows: [{"from_id": ..., "to_id": ..., "minutes": ...}, ...]"""
        travel = cls()
        for row in rows:
            travel.set(row["from_id"], row["to_id"], row["minutes"])
        return travel
