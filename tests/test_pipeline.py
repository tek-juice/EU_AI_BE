import asyncio
import json

from itin_agent.llm import LLMJSONError, parse_json_object
from itin_agent.pipeline import ItineraryPipeline, normalize_itinerary, select_candidates
from itin_agent.schemas.itinerary_schema import ItineraryOutput, TripRequirements

from fixtures import A, B, day, make_catalog

CATALOG = make_catalog()


class FakeLLM:
    """Returns scripted replies in order; a reply that is an Exception is raised."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = []

    async def complete_json(self, *, system, user):
        self.calls.append({"system": system, "user": user})
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


class CountingLoader:
    def __init__(self, catalog=CATALOG):
        self.catalog = catalog
        self.calls = 0

    async def __call__(self):
        self.calls += 1
        return self.catalog


def compose_reply(days):
    return {"days": days}


GOOD_DAYS = [
    day(1, A, ["act-1"], ("hotel-1", None, None)),
    day(2, A, ["act-2"], ("hotel-1", None, None)),
    day(3, A, ["act-5"]),
]
BAD_DAYS = [
    day(1, A, ["act-3"], ("hotel-1", None, None)),  # Bravo activity on an Alpha day
    day(2, A, ["act-2"], ("hotel-1", None, None)),
    day(3, A, ["act-5"]),
]
EXTRACTED = {"travelers": 2, "number_of_days": 3, "interests": ["wildlife"],
             "start_date": "2026-10-01"}


def run(pipeline, message="3 days for 2 people", previous=None):
    return asyncio.run(pipeline.run(message, previous_requirements=previous))


def test_happy_path_fills_names_rates_rooms_and_dates():
    llm = FakeLLM(EXTRACTED, compose_reply(GOOD_DAYS))
    result = run(ItineraryPipeline(llm, catalog_loader=CountingLoader()))

    assert result.status == "ok", result.message
    assert result.attempts == 1
    it = result.itinerary
    assert (it.trip.number_of_days, it.trip.number_of_nights, it.trip.travelers) == (3, 2, 2)
    assert it.trip.start_date == "2026-10-01" and it.trip.end_date == "2026-10-03"
    assert it.days[1].date == "2026-10-02"

    d1 = it.days[0]
    assert d1.destination.name == "Alpha Park"
    assert d1.activities[0].name == "Morning game drive"
    assert d1.activities[0].duration_minutes == 180
    assert d1.accommodation.name == "Alpha Lodge"
    # 2 travelers -> the 2-guest room needs the fewest rooms (1) and comes first
    assert d1.accommodation.rate_id == "rate-1"
    assert d1.accommodation.rooms == 1
    assert it.days[2].accommodation is None
    assert result.report.ok


def test_asks_when_required_info_is_missing_and_skips_the_catalog():
    loader = CountingLoader()
    llm = FakeLLM({"travelers": None, "number_of_days": 3})
    result = run(ItineraryPipeline(llm, catalog_loader=loader))

    assert result.status == "needs_info"
    assert "how many people" in result.question
    assert "how many days" not in result.question
    assert loader.calls == 0 and len(llm.calls) == 1
    assert result.requirements.number_of_days == 3 and result.requirements.number_of_nights == 2


def test_multi_turn_merges_previous_requirements():
    previous = TripRequirements(travelers=4, interests=["culture"])
    llm = FakeLLM({"number_of_days": 2, "interests": ["wildlife"]},
                  compose_reply([day(1, A, ["act-1"], ("hotel-1", None, None)), day(2, A, ["act-2"])]))
    result = run(ItineraryPipeline(llm, catalog_loader=CountingLoader()), "make it 2 days", previous)

    assert result.status == "ok", result.message
    assert result.requirements.travelers == 4
    assert result.requirements.interests == ["culture", "wildlife"]
    # 4 travelers: the 4-guest family rate needs one room
    assert result.itinerary.days[0].accommodation.rate_id == "rate-2"


def test_changing_days_rederives_nights():
    previous = TripRequirements(travelers=2, number_of_days=3, number_of_nights=2)
    merged = previous.merged_with(TripRequirements(number_of_days=5)).normalized()
    assert (merged.number_of_days, merged.number_of_nights) == (5, 4)


def test_repair_loop_sends_problems_back_and_recovers():
    llm = FakeLLM(EXTRACTED, compose_reply(BAD_DAYS), compose_reply(GOOD_DAYS))
    result = run(ItineraryPipeline(llm, catalog_loader=CountingLoader()))

    assert result.status == "ok"
    assert result.attempts == 2
    repair_payload = json.loads(llm.calls[2]["user"])
    assert "ACTIVITY_WRONG_DESTINATION" in repair_payload["problems"]
    assert repair_payload["previous_itinerary"]["days"][0]["activities"][0]["id"] == "act-3"


def test_fails_after_repair_limit_and_returns_the_report():
    llm = FakeLLM(EXTRACTED, compose_reply(BAD_DAYS), compose_reply(BAD_DAYS))
    result = run(ItineraryPipeline(llm, catalog_loader=CountingLoader(), max_repairs=1))

    assert result.status == "failed"
    assert result.attempts == 2
    assert not result.report.ok
    assert result.itinerary is not None  # last attempt is returned for debugging


def test_schema_errors_are_repaired_too():
    broken = {"days": [{"day_number": 1}]}  # no destination
    llm = FakeLLM(EXTRACTED, broken, compose_reply(GOOD_DAYS))
    result = run(ItineraryPipeline(llm, catalog_loader=CountingLoader()))

    assert result.status == "ok" and result.attempts == 2
    assert "SCHEMA" in json.loads(llm.calls[2]["user"])["problems"]


def test_bad_json_is_retried_once_before_giving_up():
    llm = FakeLLM(EXTRACTED, LLMJSONError("nope"), compose_reply(GOOD_DAYS))
    result = run(ItineraryPipeline(llm, catalog_loader=CountingLoader()))
    assert result.status == "ok" and result.attempts == 1

    llm = FakeLLM(LLMJSONError("a"), LLMJSONError("b"))
    result = run(ItineraryPipeline(llm, catalog_loader=CountingLoader()))
    assert result.status == "failed" and "understand" in result.message


def test_lenient_extraction_drops_invalid_fields_only():
    llm = FakeLLM({"travelers": 3, "number_of_days": 2, "budget": "lots of money"},
                  compose_reply([day(1, A, ["act-1"], ("hotel-1", None, None)), day(2, A, ["act-2"])]))
    result = run(ItineraryPipeline(llm, catalog_loader=CountingLoader()))
    assert result.status == "ok"
    assert result.requirements.budget is None and result.requirements.travelers == 3


def test_catalog_is_cached_between_runs():
    loader = CountingLoader()
    pipeline = ItineraryPipeline(
        FakeLLM(EXTRACTED, compose_reply(GOOD_DAYS), EXTRACTED, compose_reply(GOOD_DAYS)),
        catalog_loader=loader,
    )
    run(pipeline)
    run(pipeline)
    assert loader.calls == 1


def test_normalize_does_not_paper_over_wrong_ids():
    req = TripRequirements(travelers=2, number_of_days=2).normalized()
    model = ItineraryOutput.model_validate({
        "trip": {"number_of_days": 2, "number_of_nights": 1, "travelers": 2},
        "days": [day(1, A, ["act-1"], ("hotel-1", "rate-3", None)), day(2, A, [])],  # rate-3 is Bravo's
    })
    fixed = normalize_itinerary(model, req, CATALOG)
    assert fixed.days[0].accommodation.rate_id == "rate-3"  # left for the validator to flag


def test_select_candidates_ranks_by_interest_and_respects_preferences():
    req = TripRequirements(travelers=2, number_of_days=3, interests=["trekking"])
    cands = select_candidates(req, CATALOG, max_activities_per_destination=1)
    by_dest = {a["destination_id"]: a["id"] for a in cands.activities}
    assert len(cands.activities) == 3               # capped at 1 per destination
    assert by_dest[B] == "act-3"

    req = TripRequirements(travelers=2, number_of_days=3, destination_preferences=["bravo"])
    cands = select_candidates(req, CATALOG)
    assert [d["id"] for d in cands.destinations] == [B]

    req = TripRequirements(travelers=2, number_of_days=3, destination_preferences=["atlantis"])
    assert len(select_candidates(req, CATALOG).destinations) == 3   # no match -> don't restrict

    # prompt payload carries ids, no prices
    payload = json.dumps(select_candidates(req, CATALOG).to_prompt())
    assert "price" not in payload


def test_parse_json_object_handles_fences_and_noise():
    assert parse_json_object('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json_object('Sure! {"a": 1} hope that helps') == {"a": 1}
    for bad in ("", "[1, 2]", "no json here"):
        try:
            parse_json_object(bad)
        except LLMJSONError:
            continue
        raise AssertionError(f"expected LLMJSONError for {bad!r}")


def test_catalog_load_reads_the_three_api_endpoints():
    from itin_agent.catalog import Catalog

    class FakeAPI:
        def __init__(self):
            self.paths = []

        def get(self, path, params=None):
            self.paths.append(path)
            return {
                "/itinerary_data/destinations": {"destinations": [{"id": "d1", "name": "X"}]},
                "/itinerary_data/activities": {"activities": [{"id": "a1", "destination_id": "d1"}]},
                "/itinerary_data/accommodations": {
                    "accommodations": [{"id": "h1", "destination_id": "d1", "rates": [{"id": "r1"}]}]
                },
            }[path]

    api = FakeAPI()
    catalog = asyncio.run(Catalog.load(api))
    assert sorted(api.paths) == [
        "/itinerary_data/accommodations",
        "/itinerary_data/activities",
        "/itinerary_data/destinations",
    ]
    assert list(catalog.activities_by_destination["d1"])[0]["id"] == "a1"
    assert catalog.rate_index["r1"][0] == "h1"
