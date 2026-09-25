"""
LangChain tools wrapping the Everything Uganda itinerary APIs.

Each tool calls out to your backend (FastAPI/Flask -> PostgreSQL) and
returns structured data the agent/nodes can consume.

These routes now require a valid JWT (client or admin), so this module
logs in once (or uses a pre-obtained token) and attaches
"Authorization: Bearer <token>" to every request.

.env options (pick one):
  EU_API_TOKEN=<a token you already have>          # simplest, but expires
  EU_CLIENT_EMAIL=... / EU_CLIENT_PASSWORD=...      # logs in automatically
  EU_ADMIN_EMAIL=...  / EU_ADMIN_PASSWORD=...        # for admin-only routes
"""

import os
import httpx
from typing import Optional, List
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.environ.get("EU_API_URL", "http://127.0.0.1:5000/api")


_STATIC_TOKEN = os.environ.get("EU_API_TOKEN")

# Client/admin credentials, used to log in and get a token automatically
_CLIENT_EMAIL = os.environ.get("EU_CLIENT_EMAIL")
_CLIENT_PASSWORD = os.environ.get("EU_CLIENT_PASSWORD")
_ADMIN_EMAIL = os.environ.get("EU_ADMIN_EMAIL")
_ADMIN_PASSWORD = os.environ.get("EU_ADMIN_PASSWORD")

# In-memory cache so we only log in once per process run
_cached_token: Optional[str] = None


def _login(email: str, password: str, path: str) -> str:
    """Log in and return the access_token."""
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        resp = client.post(path, json={"email": email, "password": password})
        resp.raise_for_status()
        data = resp.json()
        token = data.get("access_token")
        if not token:
            raise RuntimeError(f"Login succeeded but no access_token in response: {data}")
        return token


def _get_token() -> str:
    """Return a bearer token: static token if set, else log in (client
    credentials preferred, admin as fallback), caching the result."""
    global _cached_token

    if _STATIC_TOKEN:
        return _STATIC_TOKEN

    if _cached_token:
        return _cached_token

    if _CLIENT_EMAIL and _CLIENT_PASSWORD:
        _cached_token = _login(_CLIENT_EMAIL, _CLIENT_PASSWORD, "/cliauth/login")
        return _cached_token

    if _ADMIN_EMAIL and _ADMIN_PASSWORD:
        _cached_token = _login(_ADMIN_EMAIL, _ADMIN_PASSWORD, "/admin/auth/admin_login")
        return _cached_token

    raise RuntimeError(
        "No credentials configured. Set EU_API_TOKEN, or "
        "EU_CLIENT_EMAIL/EU_CLIENT_PASSWORD, or "
        "EU_ADMIN_EMAIL/EU_ADMIN_PASSWORD in your .env file."
    )


def _auth_headers() -> dict:
    return {"Authorization": f"Bearer {_get_token()}"}


def _get(path: str, params: dict) -> dict:
    """Shared GET helper with auth and basic error handling. Retries once
    with a fresh token if the current one is rejected (401)."""
    global _cached_token
    with httpx.Client(base_url=BASE_URL, headers=_auth_headers(), timeout=10.0) as client:
        resp = client.get(path, params=params)
        if resp.status_code == 401 and not _STATIC_TOKEN:
            _cached_token = None  # force re-login
            client.headers.update(_auth_headers())
            resp = client.get(path, params=params)
        resp.raise_for_status()
        return resp.json()


def _post(path: str, payload: dict) -> dict:
    global _cached_token
    with httpx.Client(base_url=BASE_URL, headers=_auth_headers(), timeout=10.0) as client:
        resp = client.post(path, json=payload)
        if resp.status_code == 401 and not _STATIC_TOKEN:
            _cached_token = None
            client.headers.update(_auth_headers())
            resp = client.post(path, json=payload)
        resp.raise_for_status()
        return resp.json()


# ---------- get_destinations ----------

class GetDestinationsInput(BaseModel):
    region: Optional[str] = Field(None, description="Region or area in Uganda, e.g. 'Western', 'Kampala'")
    interests: Optional[List[str]] = Field(None, description="Traveler interests, e.g. ['wildlife', 'hiking']")
    max_results: int = Field(10, description="Max number of destinations to return")


@tool("get_destinations", args_schema=GetDestinationsInput)
def get_destinations(region: Optional[str] = None, interests: Optional[List[str]] = None, max_results: int = 10) -> dict:
    """Fetch candidate destinations matching a region and/or interests."""
    params = {"max_results": max_results}
    if region:
        params["region"] = region
    if interests:
        params["interests"] = ",".join(interests)
    return _get("/itinerary_data/destinations", params)


# ---------- get_activities ----------

class GetActivitiesInput(BaseModel):
    category: Optional[str] = Field(None, description="Activity category, e.g. 'adventure', 'cultural'")


@tool("get_activities", args_schema=GetActivitiesInput)
def get_activities(category: Optional[str] = None) -> dict:
    """Fetch the full list of activities (flat, across all destinations).
    Each activity carries its own destination_id — filter client-side."""
    params = {}
    if category:
        params["category"] = category
    return _get("/itinerary_data/activities", params)


# ---------- get_accommodations ----------

class GetAccommodationsInput(BaseModel):
    budget_tier: Optional[str] = Field(None, description="'budget', 'mid-range', or 'luxury'")


@tool("get_accommodations", args_schema=GetAccommodationsInput)
def get_accommodations(budget_tier: Optional[str] = None) -> dict:
    """Fetch the full list of accommodations (flat, across all destinations).
    Each accommodation carries its own destination_id — filter client-side."""
    params = {}
    if budget_tier:
        params["budget_tier"] = budget_tier
    return _get("/itinerary_data/accommodations", params)


# ---------- calculate_price ----------

class CalculatePriceInput(BaseModel):
    destination_ids: List[str] = Field(..., description="Destinations included in the itinerary")
    activity_ids: List[str] = Field(default_factory=list, description="Selected activity IDs")
    accommodation_id: Optional[str] = Field(None, description="Selected accommodation ID")
    nights: int = Field(1, description="Number of nights")
    guests: int = Field(1, description="Number of guests")


@tool("calculate_price", args_schema=CalculatePriceInput)
def calculate_price(
    destination_ids: List[str],
    activity_ids: List[str] = [],
    accommodation_id: Optional[str] = None,
    nights: int = 1,
    guests: int = 1,
) -> dict:
    """Calculate total itinerary price given selections."""
    payload = {
        "destination_ids": destination_ids,
        "activity_ids": activity_ids,
        "accommodation_id": accommodation_id,
        "nights": nights,
        "guests": guests,
    }
    return _post("/itinerary_data/pricing/calculate", payload)


# Convenience list for binding to an LLM or LangGraph node
ITINERARY_TOOLS = [get_destinations, get_activities, get_accommodations, calculate_price]