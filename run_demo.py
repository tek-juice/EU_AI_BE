"""
Try the itinerary pipeline from the command line.

Prerequisites
  1. The Flask API is running (python app.py) and has destinations,
     activities and accommodations in the database.
  2. GEMINI_API_KEY is set in your environment (or in .env, see below).
  3. pip install litellm python-dotenv   (python-dotenv is optional)

Usage (from the repo root, EU_AI_BE/)
  python run_demo.py "4 days for 2 people, we love wildlife and hiking"
  python run_demo.py                      # prompts you for the request
  python run_demo.py "..." --debug        # also show what the model saw and said
  python run_demo.py "..." --json         # print the itinerary as JSON

If the pipeline needs more information (travelers, days) it asks you a
question here in the terminal and continues with your answer.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from typing import Optional

from itin_agent.catalog import Catalog
from itin_agent.llm import LiteLLMClient
from itin_agent.pipeline import ItineraryPipeline, PipelineResult, select_candidates
from itin_agent.schemas.itinerary_schema import TripRequirements

MAX_QUESTIONS = 3


class LoggingLLM:
    """Wraps an LLM client and prints every reply (for --debug)."""

    def __init__(self, inner):
        self.inner = inner
        self.n = 0

    async def complete_json(self, *, system: str, user: str) -> dict:
        self.n += 1
        reply = await self.inner.complete_json(system=system, user=user)
        print(f"\n--- LLM reply #{self.n} ---")
        print(json.dumps(reply, indent=2)[:4000])
        return reply


def _load_env() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass


def print_itinerary(result: PipelineResult) -> None:
    it = result.itinerary
    trip = it.trip
    print(
        f"\n=== {trip.number_of_days} days / {trip.number_of_nights} nights, "
        f"{trip.travelers} traveler(s) ==="
    )
    if trip.start_date:
        print(f"    {trip.start_date} to {trip.end_date}")

    for day in it.days:
        when = f" ({day.date})" if day.date else ""
        print(f"\nDay {day.day_number}{when} - {day.destination.name or day.destination.id}")
        if day.notes:
            print(f"  {day.notes}")
        for act in day.activities:
            start = f"{act.start_time} " if act.start_time else ""
            length = f" [{act.duration_minutes} min]" if act.duration_minutes else ""
            print(f"  * {start}{act.name or act.id}{length}")
            if act.notes:
                print(f"      {act.notes}")
        stay = day.accommodation
        if stay:
            details = ", ".join(x for x in (stay.room_type, stay.meal_plan) if x)
            rooms = f" x{stay.rooms}" if stay.rooms else ""
            print(f"  Stay: {stay.name or stay.id}" + (f" ({details}{rooms})" if details else ""))
        else:
            print("  Stay: - (departure day)" if day is it.days[-1] else "  Stay: -")

    if result.report and result.report.warnings:
        print("\nWarnings")
        for issue in result.report.warnings:
            where = f"Day {issue.day_number}: " if issue.day_number else ""
            print(f"  - [{issue.code}] {where}{issue.message}")
    print(f"\n(generated in {result.attempts} attempt(s))")


def print_result(result: PipelineResult, as_json: bool = False) -> None:
    if result.status == "ok":
        if as_json:
            print(json.dumps(result.to_dict(), indent=2))
        else:
            print_itinerary(result)
    elif result.status == "failed":
        print(f"\nFAILED: {result.message}")
        if result.report:
            print("Problems found in the last attempt:")
            print(result.report.feedback(include_warnings=True) or "  (none recorded)")
        if result.itinerary and as_json:
            print(json.dumps(result.itinerary.model_dump(), indent=2))


async def amain(args: argparse.Namespace, pipeline: Optional[ItineraryPipeline] = None) -> int:
    _load_env()

    if pipeline is None:
        if not (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
            print("GEMINI_API_KEY is not set. Export it or put it in .env first.")
            return 2
        llm = LiteLLMClient(model=args.model)
        if args.debug:
            llm = LoggingLLM(llm)
        pipeline = ItineraryPipeline(llm)

    message = args.message or input("What trip do you want to plan?\n> ").strip()
    previous: Optional[TripRequirements] = None

    for _ in range(MAX_QUESTIONS + 1):
        try:
            result = await pipeline.run(message, previous_requirements=previous)
        except Exception as exc:  # network / API problems while loading the catalog
            name = type(exc).__name__
            print(f"\n{name}: {exc}")
            print(
                f"Could not load the catalog. Is the Flask API running at "
                f"{os.getenv('EU_API_URL', 'http://127.0.0.1:5000/api')}?"
            )
            return 1

        if args.debug and result.requirements:
            print("\n--- requirements ---")
            print(json.dumps(result.requirements.model_dump(), indent=2))

        if result.status == "needs_info":
            print(f"\n{result.question}")
            previous = result.requirements
            message = input("> ").strip()
            continue

        if args.debug and result.status in ("ok", "failed") and result.requirements:
            catalog = await pipeline._get_catalog()
            cands = select_candidates(result.requirements, catalog)
            print(
                f"\n--- candidates given to the model: {len(cands.destinations)} destinations, "
                f"{len(cands.activities)} activities, {len(cands.accommodations)} accommodations ---"
            )

        print_result(result, as_json=args.json)
        return 0 if result.status == "ok" else 1

    print("\nStill missing details after several questions; stopping.")
    return 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Try the itinerary pipeline")
    parser.add_argument("message", nargs="?", help="what the customer asks for")
    parser.add_argument("--model", default="gemini/gemini-2.5-flash")
    parser.add_argument("--debug", action="store_true", help="show LLM replies and requirements")
    parser.add_argument("--json", action="store_true", help="print the result as JSON")
    sys.exit(asyncio.run(amain(parser.parse_args())))


if __name__ == "__main__":
    main()