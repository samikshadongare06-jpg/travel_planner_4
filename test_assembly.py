"""
test_assembly.py — Integration tests for assembly.py
Run with: pytest test_assembly.py -v

── All tests in this file are integration tests ──
── They require MySQL running with sample data ──
── Run with: pytest test_assembly.py -v ──

Update the DB credentials in the fixture below before running.
"""

import pytest
import mysql.connector
from assembly import (
    calculate_available_hours,
    select_accommodation,
    run_scoring_pipeline,
    run_zone_pipeline,
    build_itinerary,
)


# ── DB FIXTURE ────────────────────────────────────────────────────────────────

@pytest.fixture
def db():
    connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password="password",
        database="travel_planner"
    )
    yield connection
    connection.close()


# ── INTEGRATION TESTS ─────────────────────────────────────────────────────────

def test_calculate_available_hours(db):
    """
    trip_id=1 is assumed to be a 3-day car trip in sample data.
    Total days must be 3, total hours positive,
    and day1 hours must be less than a full usable day (travel subtracted).
    """
    result = calculate_available_hours(trip_id=1, db=db)

    assert result["total_days"] == 3, (
        f"Expected 3 days, got {result['total_days']}"
    )
    assert result["total_trip_hours"] > 0, "total_trip_hours must be positive"
    assert result["day1_available_hours"] < result["usable_hours_per_day"], (
        "Day 1 should have fewer hours than a full day (travel time subtracted)"
    )
    # All values must be non-negative
    for key in ("total_trip_hours", "usable_hours_per_day",
                "day1_available_hours", "lastday_available_hours"):
        assert result[key] >= 0, f"{key} must not be negative"


def test_select_accommodation(db):
    """
    trip_id=1 has accommodation_type='4-star' in sample data.
    A matching accommodation must be returned.
    """
    result = select_accommodation(trip_id=1, db=db)

    assert result is not None, "Expected an accommodation to be returned"
    assert result["type"] == "4-star", (
        f"Expected '4-star', got '{result['type']}'"
    )
    assert "accommodation_id" in result
    assert "name" in result
    assert "zone_id" in result


def test_run_scoring_pipeline(db):
    """
    run_scoring_pipeline for trip_id=1 must return a non-empty shortlist
    that contains all must-do attractions, plus a positive total_trip_hours.
    """
    result = run_scoring_pipeline(trip_id=1, db=db)

    assert "shortlist" in result
    assert "total_trip_hours" in result

    shortlist        = result["shortlist"]
    total_trip_hours = result["total_trip_hours"]

    assert len(shortlist) > 0, "Shortlist must not be empty"
    assert total_trip_hours > 0, "total_trip_hours must be positive"

    # Every must-do attraction for this destination should be in the shortlist
    mustdo_in_shortlist = [a for a in shortlist if a["is_mustdo"]]
    assert len(mustdo_in_shortlist) > 0, (
        "At least one must-do attraction must be present in shortlist"
    )


def test_run_zone_pipeline(db):
    """
    run_zone_pipeline for trip_id=1 (3-day trip) must return a zone_day_map
    with exactly 3 entries, each having the correct keys, and a non-empty
    updated_shortlist.
    """
    # First get the shortlist from scoring
    scoring_result = run_scoring_pipeline(trip_id=1, db=db)
    shortlist      = scoring_result["shortlist"]

    result = run_zone_pipeline(trip_id=1, shortlist=shortlist, db=db)

    assert "zone_day_map" in result
    assert "updated_shortlist" in result

    zone_day_map      = result["zone_day_map"]
    updated_shortlist = result["updated_shortlist"]

    assert len(zone_day_map) == 3, (
        f"Expected 3 day entries, got {len(zone_day_map)}"
    )

    for entry in zone_day_map:
        assert "day_number"  in entry, "Missing 'day_number' key"
        assert "zone_ids"    in entry, "Missing 'zone_ids' key"
        assert "locked"      in entry, "Missing 'locked' key"

    assert len(updated_shortlist) > 0, "updated_shortlist must not be empty"


def test_build_itinerary_full(db):
    """
    Full end-to-end test for build_itinerary with trip_id=1.
    Verifies:
      - Output shape is correct
      - 3 days are returned
      - Each day has at least 3 schedule blocks
      - itinerary_days has 3 rows for trip_id=1
      - itinerary_items has rows for trip_id=1
    """
    result = build_itinerary(trip_id=1, db=db)

    # ── Output structure ──────────────────────────────────────────────────────
    assert "trip_id"       in result
    assert "destination"   in result
    assert "days"          in result
    assert "accommodation" in result

    assert result["trip_id"] == 1

    days = result["days"]
    assert len(days) == 3, f"Expected 3 days in output, got {len(days)}"

    for day in days:
        assert "day_number" in day
        assert "zone_name"  in day
        assert "schedule"   in day
        assert len(day["schedule"]) >= 3, (
            f"Day {day['day_number']} has only {len(day['schedule'])} blocks "
            f"— expected at least 3 (sleep + 2 others)"
        )

    # ── DB verification: itinerary_days ───────────────────────────────────────
    verify_cursor = db.cursor(dictionary=True)
    verify_cursor.execute(
        "SELECT COUNT(*) AS cnt FROM itinerary_days WHERE trip_id = %s",
        (1,)
    )
    days_row = verify_cursor.fetchone()
    assert days_row["cnt"] == 3, (
        f"Expected 3 rows in itinerary_days for trip_id=1, got {days_row['cnt']}"
    )

    # ── DB verification: itinerary_items ─────────────────────────────────────
    verify_cursor.execute(
        "SELECT COUNT(*) AS cnt FROM itinerary_items "
        "WHERE day_id IN ("
        "  SELECT day_id FROM itinerary_days WHERE trip_id = %s"
        ")",
        (1,)
    )
    items_row = verify_cursor.fetchone()
    verify_cursor.close()

    assert items_row["cnt"] > 0, (
        "Expected itinerary_items rows for trip_id=1 — none found"
    )
