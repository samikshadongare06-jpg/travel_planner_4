"""
test_day_builder.py — Unit tests for day_builder.py
Run with: pytest test_day_builder.py

get_fixed_blocks is a DB function — marked as integration test (skipped here).
"""

import pytest
from day_builder import (
    resolve_conflict,
    merge_empty_slots,
    find_food_for_meals,
    fill_remaining_slots,
)


# ── HELPERS ───────────────────────────────────────────────────────────────────

def _block(slot_type, start, end, attraction_id=None, meal_type=None, notes=None):
    return {
        "attraction_id": attraction_id,
        "slot_type":     slot_type,
        "meal_type":     meal_type,
        "start_time":    start,
        "end_time":      end,
        "notes":         notes,
    }


def _attraction(attraction_id, zone_id, avg_time, score,
                food_availability="none", is_mustdo=False):
    return {
        "attraction_id":     attraction_id,
        "name":              f"Attraction {attraction_id}",
        "score":             score,
        "avg_time_minutes":  avg_time,
        "is_mustdo":         is_mustdo,
        "is_strenuous":      False,
        "food_availability": food_availability,
        "zone_id":           zone_id,
        "tags":              [],
    }


# ── SECTION 1: resolve_conflict tests ─────────────────────────────────────────

def test_mustdo_always_wins():
    new_block      = _block("attraction", 1000, 1120)
    existing_block = _block("sleep", 960, 1440)
    result = resolve_conflict(
        new_block, existing_block,
        priority_order=["exploring", "meals", "rest", "sleep"],
        is_mustdo=True,
        flexibility="strict",
    )
    assert result["winner"]["slot_type"] == "attraction"


def test_sleep_protected_strict():
    new_block      = _block("attraction", 1000, 1120)
    existing_block = _block("sleep", 960, 1440)
    result = resolve_conflict(
        new_block, existing_block,
        priority_order=["exploring", "meals", "rest", "sleep"],
        is_mustdo=False,
        flexibility="strict",
    )
    assert result["winner"]["slot_type"] == "sleep"
    assert result["loser"] is None


def test_sleep_trimmed_flexible():
    new_block      = _block("attraction", 1000, 1120)
    existing_block = _block("sleep", 960, 1440)
    result = resolve_conflict(
        new_block, existing_block,
        priority_order=["exploring", "meals", "rest", "sleep"],
        is_mustdo=False,
        flexibility="flexible",
    )
    # new_block (attraction) wins; sleep trimmed by 60 min
    assert result["winner"]["slot_type"] == "attraction"
    assert result["loser"] is not None
    assert result["loser"]["slot_type"] == "sleep"
    assert result["loser"]["end_time"] == existing_block["end_time"] - 60


def test_priority_order_exploring_beats_meal():
    new_block      = _block("attraction", 780, 960)
    existing_block = _block("meal", 800, 860, meal_type="lunch")
    result = resolve_conflict(
        new_block, existing_block,
        priority_order=["exploring", "meals", "rest", "sleep"],
        is_mustdo=False,
        flexibility="moderate",
    )
    assert result["winner"]["slot_type"] == "attraction"


def test_priority_order_meal_beats_rest():
    new_block      = _block("meal", 600, 660, meal_type="breakfast")
    existing_block = _block("rest", 580, 650)
    result = resolve_conflict(
        new_block, existing_block,
        priority_order=["exploring", "meals", "rest", "sleep"],
        is_mustdo=False,
        flexibility="moderate",
    )
    assert result["winner"]["slot_type"] == "meal"


def test_travel_block_always_wins():
    new_block      = _block("attraction", 360, 540)
    existing_block = _block("travel", 360, 600)
    result = resolve_conflict(
        new_block, existing_block,
        priority_order=["exploring", "meals", "rest", "sleep"],
        is_mustdo=False,
        flexibility="flexible",
    )
    assert result["winner"]["slot_type"] == "travel"
    assert result["loser"] is None


# ── SECTION 2: merge_empty_slots tests ───────────────────────────────────────

def test_merge_finds_gap_between_blocks():
    # wake=360, sleep=1320
    # occupied: 360-540, 720-900
    # gaps: 540-720 (180 min), 900-1320 (420 min)
    schedule = [
        _block("travel",     360,  540),
        _block("attraction", 720,  900),
    ]
    windows = merge_empty_slots(schedule, wake_time=360, sleep_start=1320)
    assert len(windows) == 2
    assert windows[0]["start_time"] == 540
    assert windows[0]["end_time"]   == 720
    assert windows[1]["start_time"] == 900
    assert windows[1]["end_time"]   == 1320


def test_merge_no_gaps():
    # Blocks cover entire 360-1320 window
    schedule = [
        _block("travel",     360,  600),
        _block("meal",       600,  660),
        _block("attraction", 660,  900),
        _block("meal",       900,  960),
        _block("attraction", 960, 1200),
        _block("meal",      1200, 1320),
    ]
    windows = merge_empty_slots(schedule, wake_time=360, sleep_start=1320)
    assert windows == []


def test_merge_empty_schedule():
    # No blocks — one big window from wake to sleep
    windows = merge_empty_slots([], wake_time=360, sleep_start=1320)
    assert len(windows) == 1
    assert windows[0]["start_time"] == 360
    assert windows[0]["end_time"]   == 1320
    assert windows[0]["duration_minutes"] == 960


def test_merge_duration_calculated_correctly():
    # One block from 360-540; gap is 540-720 = 180 min
    schedule = [
        _block("travel", 360, 540),
        _block("meal",   720, 780),
    ]
    windows = merge_empty_slots(schedule, wake_time=360, sleep_start=1320)
    # First gap: 540-720
    gap = next(w for w in windows if w["start_time"] == 540)
    assert gap["duration_minutes"] == 180


# ── SECTION 3: find_food_for_meals tests ─────────────────────────────────────

def test_food_attached_to_meal():
    meal_slots = [
        _block("meal", 420, 480, meal_type="breakfast"),
    ]
    shortlist = [
        _attraction(attraction_id=10, zone_id=1, avg_time=60,
                    score=0.8, food_availability="nearby"),
    ]
    result = find_food_for_meals(meal_slots, shortlist, zone_id=1)
    assert result[0]["attraction_id"] == 10


def test_no_food_available():
    meal_slots = [
        _block("meal", 420, 480, meal_type="breakfast"),
    ]
    shortlist = [
        _attraction(attraction_id=10, zone_id=1, avg_time=60,
                    score=0.8, food_availability="none"),
    ]
    result = find_food_for_meals(meal_slots, shortlist, zone_id=1)
    assert result[0]["attraction_id"] is None


def test_food_not_reused():
    # Two meal slots, only one food attraction
    meal_slots = [
        _block("meal", 420,  480, meal_type="breakfast"),
        _block("meal", 780,  840, meal_type="lunch"),
    ]
    shortlist = [
        _attraction(attraction_id=10, zone_id=1, avg_time=60,
                    score=0.8, food_availability="integrated"),
    ]
    result = find_food_for_meals(meal_slots, shortlist, zone_id=1)
    assigned = [m["attraction_id"] for m in result if m["attraction_id"] is not None]
    # Only one assignment possible
    assert len(assigned) == 1
    # At least one slot has None
    assert any(m["attraction_id"] is None for m in result)


# ── SECTION 4: fill_remaining_slots tests ─────────────────────────────────────

def test_small_window_becomes_rest():
    # Window of 90 min (<=120) → rest block
    windows = [{"start_time": 600, "end_time": 690, "duration_minutes": 90}]
    new_blocks, _ = fill_remaining_slots(windows, shortlist=[], user_preference="efficient")
    assert len(new_blocks) == 1
    assert new_blocks[0]["slot_type"] == "rest"


def test_large_window_fills_attraction():
    # 180-min window; attraction needs 120 min; 60 min rest leftover
    windows = [{"start_time": 600, "end_time": 780, "duration_minutes": 180}]
    shortlist = [
        _attraction(attraction_id=5, zone_id=1, avg_time=120, score=0.7),
    ]
    new_blocks, _ = fill_remaining_slots(windows, shortlist, user_preference="efficient")

    types = [b["slot_type"] for b in new_blocks]
    assert "attraction" in types
    assert "rest" in types

    attr_block = next(b for b in new_blocks if b["slot_type"] == "attraction")
    rest_block  = next(b for b in new_blocks if b["slot_type"] == "rest")

    assert attr_block["start_time"] == 600
    assert attr_block["end_time"]   == 720
    assert rest_block["start_time"] == 720
    assert rest_block["end_time"]   == 780


def test_no_shortlist_all_rest():
    windows = [
        {"start_time": 600, "end_time": 900, "duration_minutes": 300},
        {"start_time": 960, "end_time": 1080, "duration_minutes": 120},
    ]
    new_blocks, updated = fill_remaining_slots(windows, shortlist=[], user_preference="efficient")
    for block in new_blocks:
        assert block["slot_type"] == "rest"


def test_updated_shortlist_removes_used():
    windows = [{"start_time": 600, "end_time": 840, "duration_minutes": 240}]
    shortlist = [
        _attraction(attraction_id=7, zone_id=1, avg_time=180, score=0.9),
        _attraction(attraction_id=8, zone_id=1, avg_time=60,  score=0.5),
    ]
    _, updated = fill_remaining_slots(windows, shortlist, user_preference="efficient")
    updated_ids = [a["attraction_id"] for a in updated]
    # Attraction 7 was placed — must be removed from shortlist
    assert 7 not in updated_ids


# ── DB functions: integration tests (skipped for now) ─────────────────────────
# get_fixed_blocks     — integration test — requires DB
# anchor_star_attraction uses only pure logic once shortlist is provided;
#   its integration test would verify correct DB-sourced data flow
