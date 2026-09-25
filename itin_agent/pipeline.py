"""
Itinerary pipeline for the Everything Uganda agent.

    extract requirements (LLM)
      -> ask for anything missing
      -> load catalog and filter candidates (code)
      -> compose itinerary from candidates only (LLM)
      -> normalize + validate (code)
      -> on errors, send the problem list back to the LLM (bounded repairs)

The LLM decides *what* to include. Code decides what is *allowed*, fills in
every name and rate from the catalog, and checks the result.
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Awaitable, Callable, Optional

from pydantic import ValidationError

from itin_agent.catalog import Catalog, TravelTimes
from itin_agent.llm import LLMClient, LLMJSONError
from itin_agent.schemas.itinerary_schema import (
    ItineraryOutput,
    TripOutput,
    TripRequirements,
    parse_iso_date,
)
from itin_agent.validator import (
    ValidationLimits,
    ValidationReport,
    validate_itinerary,
)


EXTRACT_SYSTEM = """\
You extract trip requirements for the Everything Uganda itinerary builder.

You receive JSON with: today (ISO date), already_known (requirements from
earlier in the conversation, or null) and customer_message.

Return ONLY a JSON object with these keys:
  travelers                  integer or null
  number_of_days             integer or null
  number_of_nights           integer or null (only if the customer stated it)
  start_date, end_date       "YYYY-MM-DD" or null
  budget                     number or null
  currency                   3-letter code (default "USD")
  interests                  short lowercase keywords, e.g. ["wildlife", "hiking"]
  destination_preferences    destination names the customer mentioned
  accommodation_preference   e.g. "lodge", "camp", "hotel", or null

Use null for anything the customer did not say. Never guess.
"""

COMPOSE_SYSTEM = """\
You are the Everything Uganda Itinerary Agent. Build a day-by-day itinerary
using ONLY the candidate data you are given.

RULES
1. Use only destination, activity and accommodation ids that appear in
   `candidates`. Never invent destinations, activities or accommodation.
2. One destination per day. Every activity on a day must belong to that day's
   destination (match the activity's destination_id to the day's destination).
3. Accommodation is where the travelers sleep that night. It must belong to
   that day's destination. Provide accommodation on exactly the first
   `number_of_nights` days; later days (a departure day) have
   "accommodation": null.
4. Produce exactly `number_of_days` days, numbered from 1.
5. For accommodation, choose a rate_id from that accommodation's rates whose
   max_guests suits the group, and set rooms = ceil(travelers / max_guests).
6. Keep days realistic: at most 4 activities per day and about 10 hours of
   activity time. Moving between destinations takes hours, so only change
   destination when it makes sense.
7. Match the customer's interests where the candidates allow.
8. Do not mention, include or calculate prices.

Return ONLY a JSON object shaped like this (ids only; names are filled in
later):
{
  "days": [
    {
      "day_number": 1,
      "destination": {"id": "<destination id>"},
      "accommodation": {"id": "<accommodation id>", "rate_id": "<rate id>", "rooms": 1},
      "activities": [{"id": "<activity id>", "start_time": "09:00", "notes": "<short note>"}],
      "notes": "<short day summary>"
    }
  ]
}
"""

REPAIR_INSTRUCTION = (
    "The previous itinerary broke the rules listed in `problems`. Fix every "
    "problem, keep what was already valid, follow all the rules, and return "
    "the complete corrected JSON object."
)


# --------------------------------------------------------------------------
# Results
# --------------------------------------------------------------------------

@dataclass
class PipelineResult:
    status: str  # "ok" | "needs_info" | "failed"
    requirements: Optional[TripRequirements] = None
    itinerary: Optional[ItineraryOutput] = None
    report: Optional[ValidationReport] = None
    question: Optional[str] = None
    message: Optional[str] = None
    attempts: int = 0

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "requirements": self.requirements.model_dump() if self.requirements else None,
            "itinerary": self.itinerary.model_dump() if self.itinerary else None,
            "report": self.report.to_dict() if self.report else None,
            "question": self.question,
            "message": self.message,
            "attempts": self.attempts,
        }


# --------------------------------------------------------------------------
# Candidate selection (deterministic)
# --------------------------------------------------------------------------

@dataclass
class Candidates:
    destinations: list[dict] = field(default_factory=list)
    activities: list[dict] = field(default_factory=list)
    accommodations: list[dict] = field(default_factory=list)

    def to_prompt(self) -> dict:
        return {
            "destinations": self.destinations,
            "activities": self.activities,
            "accommodations": self.accommodations,
        }


def _clip(text: Optional[str], limit: int = 160) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _haystack(*parts: Optional[str]) -> str:
    return " ".join((p or "") for p in parts).casefold()


def _interest_tokens(requirements: TripRequirements) -> list[str]:
    tokens: list[str] = []
    for interest in requirements.interests:
        phrase = interest.strip().casefold()
        if phrase:
            tokens.append(phrase)
            tokens.extend(w for w in phrase.split() if len(w) > 3)
    return list(dict.fromkeys(tokens))


def select_candidates(
    requirements: TripRequirements,
    catalog: Catalog,
    max_activities_per_destination: int = 12,
    max_accommodations_per_destination: int = 4,
) -> Candidates:
    """Narrow the catalog to a bounded, relevant slice for the prompt."""
    destinations = list(catalog.destinations.values())

    prefs = [p.strip().casefold() for p in requirements.destination_preferences if p.strip()]
    if prefs:
        matched = [
            d
            for d in destinations
            if any(
                p in _haystack(d.get("name"), d.get("slug"), d.get("region"), d.get("district"))
                or _haystack(d.get("name")) in p
                for p in prefs
            )
        ]
        if matched:  # only restrict if the request actually matched something
            destinations = matched

    tokens = _interest_tokens(requirements)
    stay_pref = (requirements.accommodation_preference or "").strip().casefold()

    out = Candidates()
    for dest in sorted(destinations, key=lambda d: d.get("name") or ""):
        dest_id = str(dest["id"])
        activities = catalog.activities_by_destination.get(dest_id, [])
        accommodations = catalog.accommodations_by_destination.get(dest_id, [])
        if not activities and not accommodations:
            continue

        out.destinations.append(
            {
                "id": dest_id,
                "name": dest.get("name"),
                "region": dest.get("region"),
                "type": dest.get("destination_type"),
                "summary": _clip(dest.get("short_description") or dest.get("description")),
            }
        )

        def score(act: dict) -> int:
            text = _haystack(act.get("activity_type"), act.get("name"), act.get("description"))
            return sum(1 for t in tokens if t in text)

        ranked = sorted(activities, key=lambda a: (-score(a), a.get("name") or ""))
        for act in ranked[:max_activities_per_destination]:
            out.activities.append(
                {
                    "id": str(act["id"]),
                    "destination_id": dest_id,
                    "name": act.get("name"),
                    "type": act.get("activity_type"),
                    "duration_minutes": act.get("duration_minutes"),
                    "summary": _clip(act.get("description")),
                }
            )

        # Prefer accommodations that have rates (needed for pricing later)
        pool = [a for a in accommodations if a.get("rates")] or accommodations
        ranked_stays = sorted(
            pool,
            key=lambda a: (
                0 if stay_pref and stay_pref in _haystack(a.get("accommodation_type")) else 1,
                -(a.get("rating") or 0),
                a.get("name") or "",
            ),
        )
        for stay in ranked_stays[:max_accommodations_per_destination]:
            out.accommodations.append(
                {
                    "id": str(stay["id"]),
                    "destination_id": dest_id,
                    "name": stay.get("name"),
                    "type": stay.get("accommodation_type"),
                    "rating": stay.get("rating"),
                    "rates": [
                        {
                            "id": str(r["id"]),
                            "room_type": r.get("room_type"),
                            "meal_plan": r.get("meal_plan"),
                            "max_guests": r.get("max_guests"),
                        }
                        for r in (stay.get("rates") or [])
                    ],
                }
            )
    return out


# --------------------------------------------------------------------------
# Normalization (deterministic: the LLM picks ids, code fills the rest)
# --------------------------------------------------------------------------

def _pick_rate(
    accommodation: dict,
    travelers: int,
    room_type: Optional[str],
    meal_plan: Optional[str],
) -> Optional[dict]:
    rates = accommodation.get("rates") or []
    if not rates:
        return None

    if room_type:
        wanted = room_type.strip().casefold()
        same_room = [r for r in rates if (r.get("room_type") or "").strip().casefold() == wanted]
        if meal_plan:
            plan = meal_plan.strip().casefold()
            same_plan = [r for r in same_room if (r.get("meal_plan") or "").strip().casefold() == plan]
            same_room = same_plan or same_room
        if same_room:
            return same_room[0]

    def rooms_needed(rate: dict) -> int:
        cap = rate.get("max_guests") or 1
        return math.ceil(travelers / cap)

    return min(rates, key=rooms_needed)  # min() keeps catalog order on ties


def normalize_itinerary(
    itinerary: ItineraryOutput,
    requirements: TripRequirements,
    catalog: Catalog,
) -> ItineraryOutput:
    """
    Make the trip block come from the requirements (not from the LLM) and fill
    names, types, durations, rates and dates from the catalog.

    Anything that references an unknown or mismatched id is left untouched so
    the validator can flag it instead of it being silently papered over.
    """
    req = requirements.normalized()
    model = itinerary.model_copy(deep=True)
    start = parse_iso_date(req.start_date)

    model.trip = TripOutput(
        number_of_days=req.number_of_days,
        number_of_nights=req.number_of_nights,
        travelers=req.travelers,
        start_date=start.isoformat() if start else None,
        end_date=(start + timedelta(days=req.number_of_days - 1)).isoformat() if start else None,
        currency=req.currency,
    )

    for day in model.days:
        if start and day.day_number >= 1:
            day.date = (start + timedelta(days=day.day_number - 1)).isoformat()

        dest = catalog.destinations.get(day.destination.id)
        if dest:
            day.destination.name = dest.get("name") or day.destination.name

        for activity in day.activities:
            source = catalog.activities.get(activity.id)
            if source:
                activity.name = source.get("name") or activity.name
                activity.activity_type = source.get("activity_type")
                activity.duration_minutes = source.get("duration_minutes")

        stay = day.accommodation
        if stay is None:
            continue
        source = catalog.accommodations.get(stay.id)
        if source is None:
            continue
        stay.name = source.get("name") or stay.name

        rate = None
        if stay.rate_id is None:
            rate = _pick_rate(source, req.travelers, stay.room_type, stay.meal_plan)
            if rate:
                stay.rate_id = str(rate["id"])
        else:
            owner = catalog.rate_index.get(stay.rate_id)
            if owner and owner[0] == stay.id:
                rate = owner[1]

        if rate:
            stay.room_type = rate.get("room_type")
            stay.meal_plan = rate.get("meal_plan")
            if stay.rooms is None:
                stay.rooms = math.ceil(req.travelers / (rate.get("max_guests") or 1))

    return model


# --------------------------------------------------------------------------
# The pipeline
# --------------------------------------------------------------------------

_QUESTION_PARTS = {
    "travelers": "how many people are travelling",
    "number_of_days": "how many days the trip should be",
}


def _lenient_requirements(raw: dict) -> TripRequirements:
    """Keep every field the model returned that validates; drop the rest."""
    fields: dict[str, Any] = {}
    for key in TripRequirements.model_fields:
        if key not in raw:
            continue
        try:
            TripRequirements.model_validate({key: raw[key]})
        except ValidationError:
            continue
        fields[key] = raw[key]
    return TripRequirements(**fields)


class ItineraryPipeline:
    def __init__(
        self,
        llm: LLMClient,
        catalog_loader: Callable[[], Awaitable[Catalog]] = Catalog.load,
        travel_times: Optional[TravelTimes] = None,
        limits: Optional[ValidationLimits] = None,
        max_repairs: int = 2,
        catalog_ttl_seconds: float = 60.0,
        max_activities_per_destination: int = 12,
        max_accommodations_per_destination: int = 4,
    ):
        self.llm = llm
        self.catalog_loader = catalog_loader
        self.travel_times = travel_times
        self.limits = limits or ValidationLimits()
        self.max_repairs = max_repairs
        self.catalog_ttl_seconds = catalog_ttl_seconds
        self.max_activities_per_destination = max_activities_per_destination
        self.max_accommodations_per_destination = max_accommodations_per_destination
        self._catalog: Optional[Catalog] = None
        self._catalog_loaded_at = 0.0

    # ---- public --------------------------------------------------------

    async def run(
        self,
        user_request: str,
        previous_requirements: Optional[TripRequirements] = None,
    ) -> PipelineResult:
        """
        Handle one customer message.

        For multi-turn use: when the result is "needs_info", store
        result.requirements, and pass it back as previous_requirements with
        the customer's next message.
        """
        try:
            requirements = await self.extract_requirements(user_request, previous_requirements)
        except (LLMJSONError, ValidationError) as exc:
            return PipelineResult(
                status="failed",
                requirements=previous_requirements,
                message=f"Could not understand the request: {exc}",
            )

        missing = requirements.missing_fields()
        if missing:
            return PipelineResult(
                status="needs_info",
                requirements=requirements,
                question=self._question(missing),
            )

        catalog = await self._get_catalog()
        if not catalog.destinations:
            return PipelineResult(
                status="failed",
                requirements=requirements,
                message="The catalog has no destinations.",
            )

        candidates = select_candidates(
            requirements,
            catalog,
            self.max_activities_per_destination,
            self.max_accommodations_per_destination,
        )
        return await self._compose_with_repairs(requirements, catalog, candidates)

    async def extract_requirements(
        self,
        user_request: str,
        previous: Optional[TripRequirements] = None,
    ) -> TripRequirements:
        payload = {
            "today": date.today().isoformat(),
            "already_known": previous.model_dump() if previous else None,
            "customer_message": user_request,
        }
        raw = await self._call_json(EXTRACT_SYSTEM, json.dumps(payload))
        extracted = _lenient_requirements(raw)
        merged = previous.merged_with(extracted) if previous else extracted
        return merged.normalized()

    # ---- internals -----------------------------------------------------

    @staticmethod
    def _question(missing: list[str]) -> str:
        parts = [_QUESTION_PARTS[m] for m in missing]
        return "To build your itinerary I still need to know " + " and ".join(parts) + "."

    async def _get_catalog(self) -> Catalog:
        now = time.monotonic()
        if self._catalog is None or now - self._catalog_loaded_at > self.catalog_ttl_seconds:
            self._catalog = await self.catalog_loader()
            self._catalog_loaded_at = now
        return self._catalog

    async def _call_json(self, system: str, user: str, attempts: int = 2) -> dict:
        last: Optional[LLMJSONError] = None
        for _ in range(attempts):
            try:
                return await self.llm.complete_json(system=system, user=user)
            except LLMJSONError as exc:
                last = exc
        assert last is not None
        raise last

    async def _compose_with_repairs(
        self,
        requirements: TripRequirements,
        catalog: Catalog,
        candidates: Candidates,
    ) -> PipelineResult:
        base_payload = {
            "requirements": requirements.model_dump(exclude={"budget", "currency"}),
            "candidates": candidates.to_prompt(),
        }
        previous_itinerary: Optional[dict] = None
        problems: Optional[str] = None
        last_model: Optional[ItineraryOutput] = None
        report = ValidationReport()
        attempts = 0

        for attempt in range(1, self.max_repairs + 2):
            attempts = attempt
            payload = dict(base_payload)
            if problems:
                payload.update(
                    previous_itinerary=previous_itinerary,
                    problems=problems,
                    instruction=REPAIR_INSTRUCTION,
                )

            report = ValidationReport()
            try:
                raw = await self._call_json(COMPOSE_SYSTEM, json.dumps(payload))
            except LLMJSONError as exc:
                report.add("NOT_JSON", f"the reply was not a valid JSON object ({exc})")
                problems = report.feedback()
                continue

            # The trip block comes from the requirements, never from the LLM.
            raw["trip"] = {
                "number_of_days": requirements.number_of_days,
                "number_of_nights": requirements.number_of_nights,
                "travelers": requirements.travelers,
            }
            try:
                parsed = ItineraryOutput.model_validate(raw)
            except ValidationError as exc:
                for err in exc.errors()[:10]:
                    where = ".".join(str(p) for p in err["loc"])
                    report.add("SCHEMA", f"{where}: {err['msg']}")
                previous_itinerary = raw
                problems = report.feedback()
                continue

            last_model = normalize_itinerary(parsed, requirements, catalog)
            report = validate_itinerary(
                last_model,
                catalog,
                requirements=requirements,
                travel_times=self.travel_times,
                limits=self.limits,
            )
            if report.ok:
                return PipelineResult(
                    status="ok",
                    requirements=requirements,
                    itinerary=last_model,
                    report=report,
                    attempts=attempts,
                )

            previous_itinerary = last_model.model_dump()
            problems = report.feedback()

        return PipelineResult(
            status="failed",
            requirements=requirements,
            itinerary=last_model,
            report=report,
            message="Could not produce a valid itinerary within the repair limit.",
            attempts=attempts,
        )
