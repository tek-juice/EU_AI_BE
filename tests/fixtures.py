"""Small fictional catalog + helpers shared by the validator and pipeline tests."""

from itin_agent.catalog import Catalog, TravelTimes

A, B, C = "dest-a", "dest-b", "dest-c"


def make_catalog() -> Catalog:
    destinations = [
        {"id": A, "name": "Alpha Park", "slug": "alpha-park", "region": "North",
         "destination_type": "park", "short_description": "Savannah wildlife park"},
        {"id": B, "name": "Bravo Forest", "slug": "bravo-forest", "region": "South",
         "destination_type": "forest", "short_description": "Rainforest trekking"},
        {"id": C, "name": "Charlie Lake", "slug": "charlie-lake", "region": "Central",
         "destination_type": "lake", "short_description": "Lakeside town"},
    ]
    activities = [
        {"id": "act-1", "destination_id": A, "name": "Morning game drive",
         "activity_type": "wildlife", "duration_minutes": 180, "description": "Wildlife drive"},
        {"id": "act-2", "destination_id": A, "name": "River boat cruise",
         "activity_type": "cruise", "duration_minutes": 120, "description": "Boat trip"},
        {"id": "act-3", "destination_id": B, "name": "Forest trek",
         "activity_type": "trekking", "duration_minutes": 480, "description": "Long trek",
         "rates": [{"id": "ar-3", "price": 100.0, "min_people": 1, "max_people": 8}]},
        {"id": "act-4", "destination_id": C, "name": "Lake hike",
         "activity_type": "hiking", "duration_minutes": 240, "description": "Hike"},
        {"id": "act-5", "destination_id": A, "name": "Sunset drive",
         "activity_type": "wildlife", "duration_minutes": 300, "description": "Long drive"},
        {"id": "act-6", "destination_id": A, "name": "Full-day safari",
         "activity_type": "wildlife", "duration_minutes": 300, "description": "Long safari"},
        {"id": "act-7", "destination_id": A, "name": "Night walk",
         "activity_type": "walk", "duration_minutes": 300, "description": "Night walk"},
    ]
    accommodations = [
        {"id": "hotel-1", "destination_id": A, "name": "Alpha Lodge",
         "accommodation_type": "lodge", "rating": 4.5,
         "rates": [
             {"id": "rate-1", "room_type": "Double", "meal_plan": "Full board", "max_guests": 2},
             {"id": "rate-2", "room_type": "Family", "meal_plan": "Full board", "max_guests": 4},
         ]},
        {"id": "hotel-2", "destination_id": B, "name": "Bravo Camp",
         "accommodation_type": "camp", "rating": 4.0,
         "rates": [{"id": "rate-3", "room_type": "Tent", "meal_plan": "Half board", "max_guests": 2}]},
        {"id": "hotel-3", "destination_id": C, "name": "Charlie Hotel",
         "accommodation_type": "hotel", "rating": 3.5,
         "rates": [{"id": "rate-4", "room_type": "Twin", "meal_plan": "B&B", "max_guests": 3}]},
    ]
    return Catalog(destinations, activities, accommodations)


def day(n, dest, activities=(), stay=None, **extra):
    """Build a day dict. `stay` is (accommodation_id, rate_id, rooms) or None."""
    out = {
        "day_number": n,
        "destination": {"id": dest},
        "activities": [{"id": a} for a in activities],
    }
    if stay:
        acc_id, rate_id, rooms = stay
        out["accommodation"] = {"id": acc_id, "rate_id": rate_id, "rooms": rooms}
    out.update(extra)
    return out


def itinerary(days, travelers=2, nights=None):
    n = len(days)
    return {
        "trip": {
            "number_of_days": n,
            "number_of_nights": n - 1 if nights is None else nights,
            "travelers": travelers,
        },
        "days": days,
    }


def valid_three_day(travelers=2):
    return itinerary(
        [
            day(1, A, ["act-1"], ("hotel-1", "rate-1", 1)),
            day(2, A, ["act-2"], ("hotel-1", "rate-1", 1)),
            day(3, A, ["act-5"]),
        ],
        travelers=travelers,
    )


def travel(minutes_ab=None):
    tt = TravelTimes()
    if minutes_ab is not None:
        tt.set(A, B, minutes_ab)
    return tt
