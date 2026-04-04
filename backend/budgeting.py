"""
budgeting.py

Lightweight budget estimator to support the UI.
This does NOT book anything; it only creates a rough, explainable
estimate to help users avoid overpricing.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List


@dataclass(frozen=True)
class TripSettings:
    num_people: int
    travel_mode: str
    accommodation_type: str
    meals_per_day: int
    start_date: Any
    end_date: Any


def _parse_date(d: Any):
    if isinstance(d, datetime):
        return d.date()
    if hasattr(d, "isoformat") and not isinstance(d, str):
        # mysql-connector typically returns date objects
        return d
    return datetime.strptime(d, "%Y-%m-%d").date()


def _estimate_accommodation_per_day(num_people: int, accommodation_type: str) -> float:
    # Simple per-person-per-day approximations (INR) for a “rough planning” budget.
    per_person_map = {
        "budget": 1200,
        "3-star": 2200,
        "4-star": 3300,
        "5-star": 5200,
    }
    per_person = per_person_map.get(accommodation_type, per_person_map["3-star"])
    return per_person * max(int(num_people or 1), 1)


def _estimate_travel_total(num_people: int, travel_mode: str) -> float:
    # “Total” travel is split across day 1 and last day for a typical itinerary.
    per_group_map = {
        "car": 2200,
        "train": 3800,
        "flight": 6500,
    }
    base = per_group_map.get(travel_mode, per_group_map["car"])
    return base * max(int(num_people or 1), 1) * 0.35  # scale down to keep it “rough”


def _estimate_food_per_day(num_people: int, meals_per_day: int) -> float:
    # Rough average food spend per meal per person.
    per_meal_per_person = 550
    return per_meal_per_person * max(int(meals_per_day or 3), 1) * max(int(num_people or 1), 1)


def estimate_trip_budget(trip_row: Dict[str, Any]) -> Dict[str, Any]:
    """
    trip_row: a dict from DB containing at least:
      - num_people
      - travel_mode
      - accommodation_type
      - meals_per_day
      - start_date, end_date

    Returns:
      {
        "total_trip_budget": float,
        "days": [
          {"day_number": 1, "total": float, "categories": {...}},
           ...
        ]
      }
    """
    start = _parse_date(trip_row["start_date"])
    end = _parse_date(trip_row["end_date"])

    num_days = max((end - start).days, 1)

    num_people = int(trip_row.get("num_people") or 1)
    travel_mode = str(trip_row["travel_mode"])
    accommodation_type = str(trip_row["accommodation_type"])
    meals_per_day = int(trip_row.get("meals_per_day") or 3)

    stay_daily = _estimate_accommodation_per_day(num_people, accommodation_type)
    food_daily = _estimate_food_per_day(num_people, meals_per_day)
    travel_total = _estimate_travel_total(num_people, travel_mode)

    # Split travel into day 1 and last day.
    travel_day1 = travel_total * 0.55
    travel_last = travel_total * 0.45

    days: List[Dict[str, Any]] = []
    total_trip_budget = 0.0

    for day_number in range(1, num_days + 1):
        travel_cost = 0.0
        if day_number == 1:
            travel_cost = travel_day1
        elif day_number == num_days and num_days != 1:
            travel_cost = travel_last

        # Shopping is a “wildcard” bucket: 15% of (food + stay + travel).
        base_for_shopping = food_daily + stay_daily + travel_cost
        shopping = base_for_shopping * 0.15

        # Misc covers snacks/entry retries/contingency: 8%.
        misc = base_for_shopping * 0.08

        total = stay_daily + food_daily + travel_cost + shopping + misc
        total = round(total)

        categories = {
            "accommodation": round(stay_daily),
            "food": round(food_daily),
            "travel": round(travel_cost),
            "shopping": round(shopping),
            "misc": round(misc),
        }

        days.append({
            "day_number": day_number,
            "total": total,
            "categories": categories,
        })
        total_trip_budget += total

    return {
        "total_trip_budget": round(total_trip_budget),
        "days": days,
    }

