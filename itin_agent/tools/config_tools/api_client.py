import os
import requests


class EuitineraryAPI:
    """Client for the Everything Uganda REST API."""

    def __init__(self):
        self.base_url = os.getenv(
            "EU_API_URL",
            "http://127.0.0.1:5000/api"
        )

    def get(self, endpoint: str, params: dict | None = None):
        url = f"{self.base_url}{endpoint}"

        response = requests.get(
            url,
            params=params,
            timeout=30
        )

        response.raise_for_status()

        return response.json()