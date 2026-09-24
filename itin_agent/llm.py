"""
The pipeline talks to the model through one small interface, so tests can use
a fake and you can swap providers without touching pipeline logic.
"""

from __future__ import annotations

import json
import re
from typing import Optional, Protocol


class LLMJSONError(ValueError):
    """The model's reply could not be parsed as a JSON object."""


class LLMClient(Protocol):
    async def complete_json(self, *, system: str, user: str) -> dict:
        """Return the model's reply parsed as a JSON object."""
        ...


def parse_json_object(text: Optional[str]) -> dict:
    """Parse a JSON object out of a model reply (tolerates ``` fences)."""
    if not text or not text.strip():
        raise LLMJSONError("empty response")

    cleaned = text.strip()
    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", cleaned, re.DOTALL)
    if fenced:
        cleaned = fenced.group(1)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end <= start:
            raise LLMJSONError("no JSON object found in response")
        try:
            data = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError as exc:
            raise LLMJSONError(f"invalid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise LLMJSONError("response JSON is not an object")
    return data


class LiteLLMClient:
    """
    LiteLLM-backed client. Defaults match itin_agent/config.yml
    (gemini/gemini-2.5-flash). With api_key=None, LiteLLM reads
    GEMINI_API_KEY from the environment.
    """

    def __init__(
        self,
        model: str = "gemini/gemini-2.5-flash",
        api_key: Optional[str] = None,
        temperature: float = 0.2,
        timeout: float = 60.0,
    ):
        self.model = model
        self.api_key = api_key
        self.temperature = temperature
        self.timeout = timeout

    async def complete_json(self, *, system: str, user: str) -> dict:
        import litellm  # imported lazily so tests don't need it

        kwargs = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": self.temperature,
            "timeout": self.timeout,
            "response_format": {"type": "json_object"},
        }
        if self.api_key:
            kwargs["api_key"] = self.api_key

        response = await litellm.acompletion(**kwargs)
        return parse_json_object(response.choices[0].message.content)
