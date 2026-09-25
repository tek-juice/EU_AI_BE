import copy

from itin_agent.schemas.itinerary_schema import TripRequirements
from itin_agent.validator import validate_itinerary

from fixtures import (A, B, day, itinerary, make_catalog, travel, valid_three_day)

CATALOG = make_catalog()


def codes(report, severity=None):
    issues = report.issues
    if severity == "error":
        issues = report.errors
    elif severity == "warning":
        issues = report.warnings
    return [i.code for i in issues]


def test_valid_itinerary_passes():
    report = validate_itinerary(valid_three_day(), CATALOG)
    assert report.ok, report.feedback()


def test_schema_error_is_reported_not_raised():
    report = validate_itinerary({"days": []}, CATALOG)
    assert not report.ok
    assert "SCHEMA" in codes(report)


def test_unknown_ids():
    it = valid_three_day()
    it["days"][0]["activities"] = [{"id": "made-up"}]
    it["days"][1]["accommodation"]["id"] = "made-up-hotel"
    it["days"][2]["destination"]["id"] = "made-up-dest"
    got = codes(validate_itinerary(it, CATALOG), "error")
    assert "ACTIVITY_UNKNOWN" in got
    assert "ACCOMMODATION_UNKNOWN" in got
    assert "DESTINATION_UNKNOWN" in got


def test_activity_must_belong_to_the_days_destination():
    it = valid_three_day()
    it["days"][0]["activities"] = [{"id": "act-3"}]  # a Bravo activity on an Alpha day
    report = validate_itinerary(it, CATALOG)
    assert "ACTIVITY_WRONG_DESTINATION" in codes(report, "error")
    assert "Bravo Forest" in report.feedback() and "Alpha Park" in report.feedback()


def test_accommodation_must_belong_to_the_days_destination():
    it = valid_three_day()
    it["days"][0]["accommodation"] = {"id": "hotel-2", "rate_id": "rate-3", "rooms": 1}
    assert "ACCOMMODATION_WRONG_DESTINATION" in codes(validate_itinerary(it, CATALOG), "error")


def test_day_count_and_numbering():
    it = valid_three_day()
    it["trip"]["number_of_days"] = 4
    it["trip"]["number_of_nights"] = 3
    assert "DAY_COUNT" in codes(validate_itinerary(it, CATALOG), "error")

    it = valid_three_day()
    it["days"][2]["day_number"] = 5
    assert "DAY_NUMBERING" in codes(validate_itinerary(it, CATALOG), "error")


def test_nights_must_be_consistent_with_days():
    it = valid_three_day()
    it["trip"]["number_of_nights"] = 7
    assert "NIGHTS_INCONSISTENT" in codes(validate_itinerary(it, CATALOG), "error")


def test_missing_and_extra_accommodation():
    it = valid_three_day()
    it["days"][1].pop("accommodation")
    assert "MISSING_ACCOMMODATION" in codes(validate_itinerary(it, CATALOG), "error")

    it = valid_three_day()
    it["days"][2]["accommodation"] = {"id": "hotel-1", "rate_id": "rate-1", "rooms": 1}
    assert "EXTRA_ACCOMMODATION" in codes(validate_itinerary(it, CATALOG), "error")


def test_requirements_mismatch():
    reqs = TripRequirements(travelers=5, number_of_days=3)
    got = codes(validate_itinerary(valid_three_day(travelers=2), CATALOG, requirements=reqs), "error")
    assert "TRAVELERS_MISMATCH" in got
    reqs = TripRequirements(travelers=2, number_of_days=4)
    got = codes(validate_itinerary(valid_three_day(), CATALOG, requirements=reqs), "error")
    assert "DAYS_MISMATCH" in got and "NIGHTS_MISMATCH" in got


def test_day_overload():
    it = itinerary(
        [
            day(1, A, ["act-5", "act-6", "act-7"], ("hotel-1", "rate-1", 1)),  # 900 min
            day(2, A, ["act-1"]),
        ]
    )
    assert "DAY_OVERLOADED" in codes(validate_itinerary(it, CATALOG), "error")


def test_duplicate_activity_same_day_is_error_and_repeat_is_warning():
    it = valid_three_day()
    it["days"][0]["activities"] = [{"id": "act-1"}, {"id": "act-1"}]
    assert "ACTIVITY_DUPLICATE" in codes(validate_itinerary(it, CATALOG), "error")

    it = valid_three_day()
    it["days"][1]["activities"] = [{"id": "act-1"}]
    report = validate_itinerary(it, CATALOG)
    assert report.ok
    assert "ACTIVITY_REPEATED" in codes(report, "warning")


def test_room_capacity():
    # 5 travelers, 2-guest room
    it = itinerary(
        [day(1, A, ["act-1"], ("hotel-1", "rate-1", 2)), day(2, A, ["act-2"])],
        travelers=5,
    )
    assert "ROOM_CAPACITY" in codes(validate_itinerary(it, CATALOG), "error")

    it["days"][0]["accommodation"]["rooms"] = 3
    assert validate_itinerary(it, CATALOG).ok

    it["days"][0]["accommodation"]["rooms"] = None
    report = validate_itinerary(it, CATALOG)
    assert report.ok
    assert "NEEDS_MULTIPLE_ROOMS" in codes(report, "warning")


def test_rate_must_belong_to_the_accommodation():
    it = valid_three_day()
    it["days"][0]["accommodation"]["rate_id"] = "rate-3"  # belongs to hotel-2
    assert "RATE_MISMATCH" in codes(validate_itinerary(it, CATALOG), "error")


def test_activity_group_size_warning():
    it = itinerary(
        [day(1, B, ["act-3"], ("hotel-2", "rate-3", 5)), day(2, B, ["act-3"])],
        travelers=10,
    )
    assert "ACTIVITY_GROUP_SIZE" in codes(validate_itinerary(it, CATALOG), "warning")


def test_transfer_between_destinations():
    it = itinerary(
        [
            day(1, A, ["act-1"], ("hotel-1", "rate-1", 1)),
            day(2, B, ["act-3"], ("hotel-2", "rate-3", 1)),
            day(3, B, []),
        ]
    )
    # unknown -> warning only
    report = validate_itinerary(it, CATALOG, travel_times=travel())
    assert "TRAVEL_TIME_UNKNOWN" in codes(report, "warning")

    # known and fine (240 transfer + 480 trek = 720, exactly at the limit)
    assert validate_itinerary(it, CATALOG, travel_times=travel(240)).ok

    # too long
    report = validate_itinerary(it, CATALOG, travel_times=travel(600))
    assert "TRANSFER_TOO_LONG" in codes(report, "error")
    assert "DAY_OVERLOADED" in codes(report, "error")


def test_date_range_and_feedback_text():
    it = valid_three_day()
    it["trip"]["start_date"] = "2026-10-01"
    it["trip"]["end_date"] = "2026-10-09"
    report = validate_itinerary(it, CATALOG)
    assert "DATE_RANGE" in codes(report, "error")
    assert "[DATE_RANGE]" in report.feedback()


def test_accepts_model_instance_and_leaves_input_untouched():
    from itin_agent.schemas.itinerary_schema import ItineraryOutput

    raw = valid_three_day()
    snapshot = copy.deepcopy(raw)
    assert validate_itinerary(ItineraryOutput.model_validate(raw), CATALOG).ok
    assert validate_itinerary(raw, CATALOG).ok
    assert raw == snapshot
