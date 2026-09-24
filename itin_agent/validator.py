"""
validate_itinerary: enforce the itinerary rules in code instead of in the prompt.

Pure Python, no LLM and no network. Works on an ItineraryOutput or a plain
dict, checks it against a Catalog, and returns a ValidationReport.

Errors mean "this itinerary is wrong, send it back for repair".
Warnings mean "worth showing, but not worth a repair round-trip".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Union

from pydantic import ValidationError

from itin_agent.catalog import Catalog, TravelTimes
from itin_agent.schemas.itinerary_schema import (
    ItineraryOutput,
    TripRequirements,
    parse_iso_date,
)

ERROR = "error"
WARNING = "warning"


@dataclass(frozen=True)
class ValidationLimits:
    max_activities_per_day: int = 4
    max_day_minutes: int = 720        # activities + transfer, per day
    max_transfer_minutes: int = 480   # a single destination change


@dataclass
class Issue:
    code: str
    message: str
    severity: str = ERROR
    day_number: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
            "day_number": self.day_number,
        }


@dataclass
class ValidationReport:
    issues: list[Issue] = field(default_factory=list)

    def add(
        self,
        code: str,
        message: str,
        severity: str = ERROR,
        day: Optional[int] = None,
    ) -> None:
        self.issues.append(Issue(code, message, severity, day))

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == ERROR]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == WARNING]

    @property
    def ok(self) -> bool:
        return not self.errors

    def feedback(self, include_warnings: bool = False) -> str:
        """Plain-text problem list, written to be fed back to the LLM."""
        issues = self.issues if include_warnings else self.errors
        lines = []
        for issue in issues:
            where = f"Day {issue.day_number}: " if issue.day_number else ""
            lines.append(f"- [{issue.code}] {where}{issue.message}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "errors": [i.to_dict() for i in self.errors],
            "warnings": [i.to_dict() for i in self.warnings],
        }


def _norm(value: Optional[str]) -> str:
    return (value or "").strip().casefold()


def validate_itinerary(
    itinerary: Union[ItineraryOutput, dict],
    catalog: Catalog,
    requirements: Optional[TripRequirements] = None,
    travel_times: Optional[TravelTimes] = None,
    limits: Optional[ValidationLimits] = None,
) -> ValidationReport:
    limits = limits or ValidationLimits()
    report = ValidationReport()

    # ---- 0. structure ----------------------------------------------------
    if isinstance(itinerary, ItineraryOutput):
        model = itinerary
    else:
        try:
            model = ItineraryOutput.model_validate(itinerary)
        except ValidationError as exc:
            for err in exc.errors()[:10]:
                where = ".".join(str(part) for part in err["loc"])
                report.add("SCHEMA", f"{where}: {err['msg']}")
            return report

    trip, days = model.trip, model.days
    travelers = trip.travelers

    # ---- 1. trip-level consistency --------------------------------------
    if len(days) != trip.number_of_days:
        report.add(
            "DAY_COUNT",
            f"trip says {trip.number_of_days} days but {len(days)} day "
            f"entries were provided",
        )

    if [d.day_number for d in days] != list(range(1, len(days) + 1)):
        report.add(
            "DAY_NUMBERING",
            "day_number values must be 1, 2, 3, ... in order with no gaps",
        )

    if trip.number_of_nights not in (trip.number_of_days - 1, trip.number_of_days):
        report.add(
            "NIGHTS_INCONSISTENT",
            f"{trip.number_of_nights} nights is not consistent with "
            f"{trip.number_of_days} days",
        )

    if requirements is not None:
        req = requirements.normalized()
        if req.travelers and req.travelers != trip.travelers:
            report.add(
                "TRAVELERS_MISMATCH",
                f"requested {req.travelers} travelers, itinerary has "
                f"{trip.travelers}",
            )
        if req.number_of_days and req.number_of_days != trip.number_of_days:
            report.add(
                "DAYS_MISMATCH",
                f"requested {req.number_of_days} days, itinerary has "
                f"{trip.number_of_days}",
            )
        if req.number_of_nights is not None and (
            req.number_of_nights != trip.number_of_nights
        ):
            report.add(
                "NIGHTS_MISMATCH",
                f"requested {req.number_of_nights} nights, itinerary has "
                f"{trip.number_of_nights}",
            )

    start, end = parse_iso_date(trip.start_date), parse_iso_date(trip.end_date)
    if start and end and (end - start).days + 1 != trip.number_of_days:
        report.add(
            "DATE_RANGE",
            f"{trip.start_date} to {trip.end_date} does not span "
            f"{trip.number_of_days} days",
        )

    # ---- 2. per-day checks ----------------------------------------------
    activity_minutes: list[int] = []
    first_seen_on_day: dict[str, int] = {}

    for idx, day in enumerate(days):
        n = day.day_number
        dest_id = day.destination.id
        dest = catalog.destinations.get(dest_id)

        # destination
        if dest is None:
            report.add(
                "DESTINATION_UNKNOWN",
                f"destination id '{dest_id}' is not in the catalog",
                day=n,
            )
        elif day.destination.name and _norm(day.destination.name) != _norm(dest["name"]):
            report.add(
                "DESTINATION_NAME_MISMATCH",
                f"destination name '{day.destination.name}' does not match "
                f"catalog name '{dest['name']}'",
                WARNING,
                day=n,
            )

        # activities
        if not day.activities:
            report.add("EMPTY_DAY", "no activities planned", WARNING, day=n)
        if len(day.activities) > limits.max_activities_per_day:
            report.add(
                "TOO_MANY_ACTIVITIES",
                f"{len(day.activities)} activities (recommended max "
                f"{limits.max_activities_per_day})",
                WARNING,
                day=n,
            )

        minutes = 0
        ids_today: set[str] = set()
        for act_out in day.activities:
            act = catalog.activities.get(act_out.id)
            if act is None:
                report.add(
                    "ACTIVITY_UNKNOWN",
                    f"activity id '{act_out.id}' is not in the catalog",
                    day=n,
                )
                continue

            label = act.get("name") or act_out.id

            if act_out.id in ids_today:
                report.add(
                    "ACTIVITY_DUPLICATE",
                    f"'{label}' appears more than once on the same day",
                    day=n,
                )
            elif act_out.id in first_seen_on_day:
                report.add(
                    "ACTIVITY_REPEATED",
                    f"'{label}' was already scheduled on day "
                    f"{first_seen_on_day[act_out.id]}",
                    WARNING,
                    day=n,
                )
            ids_today.add(act_out.id)
            first_seen_on_day.setdefault(act_out.id, n)

            if dest is not None and str(act.get("destination_id")) != dest_id:
                actual = catalog.destinations.get(str(act.get("destination_id")), {})
                report.add(
                    "ACTIVITY_WRONG_DESTINATION",
                    f"'{label}' is in {actual.get('name', 'another destination')}, "
                    f"not in {dest['name']}",
                    day=n,
                )

            minutes += act.get("duration_minutes") or 0

            rates = act.get("rates") or []
            if act_out.rate_id and act_out.rate_id not in {str(r["id"]) for r in rates}:
                report.add(
                    "ACTIVITY_RATE_UNKNOWN",
                    f"rate '{act_out.rate_id}' does not belong to '{label}'",
                    day=n,
                )
            if rates and not any(
                (r.get("min_people") or 1) <= travelers <= (r.get("max_people") or 10**9)
                for r in rates
            ):
                report.add(
                    "ACTIVITY_GROUP_SIZE",
                    f"'{label}' has no rate that fits a group of {travelers}",
                    WARNING,
                    day=n,
                )
        activity_minutes.append(minutes)

        # accommodation: nights are the first `number_of_nights` days
        should_stay = idx < trip.number_of_nights
        stay = day.accommodation
        if stay is None:
            if should_stay:
                report.add(
                    "MISSING_ACCOMMODATION",
                    "a place to sleep is required for this night",
                    day=n,
                )
            continue
        if not should_stay:
            report.add(
                "EXTRA_ACCOMMODATION",
                f"accommodation is only needed for the first "
                f"{trip.number_of_nights} days (this is a departure day)",
                day=n,
            )

        acc = catalog.accommodations.get(stay.id)
        if acc is None:
            report.add(
                "ACCOMMODATION_UNKNOWN",
                f"accommodation id '{stay.id}' is not in the catalog",
                day=n,
            )
            continue

        acc_label = acc.get("name") or stay.id
        if dest is not None and str(acc.get("destination_id")) != dest_id:
            report.add(
                "ACCOMMODATION_WRONG_DESTINATION",
                f"'{acc_label}' is not in {dest['name']}, where the travelers "
                f"stay this night",
                day=n,
            )

        if requirements is not None and requirements.accommodation_preference:
            if _norm(requirements.accommodation_preference) not in _norm(
                acc.get("accommodation_type")
            ):
                report.add(
                    "ACCOMMODATION_PREFERENCE",
                    f"'{acc_label}' is a {acc.get('accommodation_type')}; "
                    f"requested '{requirements.accommodation_preference}'",
                    WARNING,
                    day=n,
                )

        if stay.rate_id:
            owner_rate = catalog.rate_index.get(stay.rate_id)
            if owner_rate is None or owner_rate[0] != stay.id:
                report.add(
                    "RATE_MISMATCH",
                    f"rate '{stay.rate_id}' does not belong to '{acc_label}'",
                    day=n,
                )
            else:
                capacity = owner_rate[1].get("max_guests") or 0
                if capacity > 0:
                    if stay.rooms is None and travelers > capacity:
                        report.add(
                            "NEEDS_MULTIPLE_ROOMS",
                            f"{travelers} travelers exceed the {capacity}-guest "
                            f"room; set rooms",
                            WARNING,
                            day=n,
                        )
                    elif stay.rooms is not None and stay.rooms * capacity < travelers:
                        report.add(
                            "ROOM_CAPACITY",
                            f"{stay.rooms} room(s) of {capacity} cannot hold "
                            f"{travelers} travelers",
                            day=n,
                        )

    # ---- 3. transfers between destinations ------------------------------
    day_minutes = list(activity_minutes)
    warned_pairs: set[frozenset] = set()

    for idx in range(1, len(days)):
        prev_id, cur_id = days[idx - 1].destination.id, days[idx].destination.id
        if prev_id == cur_id:
            continue
        if prev_id not in catalog.destinations or cur_id not in catalog.destinations:
            continue

        transfer = travel_times.get(prev_id, cur_id) if travel_times else None
        prev_name = catalog.destinations[prev_id]["name"]
        cur_name = catalog.destinations[cur_id]["name"]
        n = days[idx].day_number

        if transfer is None:
            pair = frozenset((prev_id, cur_id))
            if pair not in warned_pairs:
                warned_pairs.add(pair)
                report.add(
                    "TRAVEL_TIME_UNKNOWN",
                    f"no travel time on file between {prev_name} and {cur_name}",
                    WARNING,
                    day=n,
                )
            continue

        day_minutes[idx] += transfer
        if transfer > limits.max_transfer_minutes:
            report.add(
                "TRANSFER_TOO_LONG",
                f"{prev_name} to {cur_name} takes about {transfer} minutes "
                f"(limit {limits.max_transfer_minutes})",
                day=n,
            )

    for idx, total in enumerate(day_minutes):
        if total > limits.max_day_minutes:
            report.add(
                "DAY_OVERLOADED",
                f"{total} minutes of activities and transfers "
                f"(limit {limits.max_day_minutes})",
                day=days[idx].day_number,
            )

    return report
