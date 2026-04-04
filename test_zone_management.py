"""
test_zone_management.py — Unit tests for zone_management.py
Run with: pytest test_zone_management.py

DB-dependent functions (get_zone_adjacency, assign_anchor_zones,
order_middle_zones) are marked as integration tests and skipped here.
"""

import math
import pytest
from zone_management import (
    calculate_zone_stats,
    drop_weak_zones,
    distribute_zones_to_days,
)


# ── HELPERS ──────────────────────────────────────────────────────────────────

def _make_attraction(attraction_id, zone_id, avg_time_minutes, score, is_mustdo=False):
    """Minimal attraction dict matching build_shortlist output format."""
    return {
        "attraction_id":     attraction_id,
        "name":              f"Attraction {attraction_id}",
        "score":             score,
        "avg_time_minutes":  avg_time_minutes,
        "is_mustdo":         is_mustdo,
        "is_strenuous":      False,
        "food_availability": "none",
        "zone_id":           zone_id,
        "tags":              [],
    }


def _make_zone(zone_id, total_time, top_score, attraction_count=2):
    """Minimal zone_stats dict matching calculate_zone_stats output format."""
    return {
        "zone_id":          zone_id,
        "total_time":       total_time,
        "attraction_count": attraction_count,
        "top_score":        top_score,
    }


# ── SECTION 1: calculate_zone_stats tests ────────────────────────────────────

def test_zone_stats_groups_correctly():
    shortlist = [
        _make_attraction(1, zone_id=1, avg_time_minutes=120, score=0.8),
        _make_attraction(2, zone_id=1, avg_time_minutes=90,  score=0.6),
        _make_attraction(3, zone_id=2, avg_time_minutes=180, score=0.7),
    ]
    zone_stats, avg, _ = calculate_zone_stats(shortlist)

    by_id = {z["zone_id"]: z for z in zone_stats}

    assert by_id[1]["total_time"] == 210
    assert by_id[1]["attraction_count"] == 2
    assert by_id[1]["top_score"] == pytest.approx(0.8)

    assert by_id[2]["total_time"] == 180
    assert by_id[2]["attraction_count"] == 1
    assert by_id[2]["top_score"] == pytest.approx(0.7)

    assert avg == pytest.approx((210 + 180) / 2)


def test_zone_stats_sorted_by_top_score():
    shortlist = [
        _make_attraction(1, zone_id=1, avg_time_minutes=120, score=0.8),
        _make_attraction(2, zone_id=2, avg_time_minutes=180, score=0.5),
        _make_attraction(3, zone_id=3, avg_time_minutes=90,  score=0.9),
    ]
    zone_stats, _, _ = calculate_zone_stats(shortlist)

    scores = [z["top_score"] for z in zone_stats]
    assert scores == sorted(scores, reverse=True)
    assert zone_stats[0]["top_score"] == pytest.approx(0.9)


def test_zone_stats_empty_shortlist():
    result = calculate_zone_stats([])
    assert result == ([], 0.0, 0.0)


def test_zone_stats_single_zone():
    shortlist = [
        _make_attraction(1, zone_id=1, avg_time_minutes=120, score=0.7),
        _make_attraction(2, zone_id=1, avg_time_minutes=90,  score=0.5),
    ]
    zone_stats, avg, sd = calculate_zone_stats(shortlist)

    assert len(zone_stats) == 1
    assert sd == pytest.approx(0.0)


def test_zone_stats_std_deviation_correct():
    # From spec example: zone1 total=270, zone2 total=330
    # avg=300, variance=900, sd=30.0
    shortlist = [
        _make_attraction(1, zone_id=1, avg_time_minutes=120, score=0.8),
        _make_attraction(2, zone_id=1, avg_time_minutes=90,  score=0.6),
        _make_attraction(3, zone_id=1, avg_time_minutes=60,  score=0.5),
        _make_attraction(4, zone_id=2, avg_time_minutes=180, score=0.7),
        _make_attraction(5, zone_id=2, avg_time_minutes=150, score=0.4),
    ]
    zone_stats, avg, sd = calculate_zone_stats(shortlist)

    by_id = {z["zone_id"]: z for z in zone_stats}
    assert by_id[1]["total_time"] == 270
    assert by_id[2]["total_time"] == 330
    assert avg == pytest.approx(300.0)
    assert sd == pytest.approx(30.0)


# ── SECTION 2: drop_weak_zones tests ─────────────────────────────────────────

def test_drop_zones_removes_weak():
    # threshold = 200 - 100 = 100; zone1.total_time=100, NOT < 100 → keep both
    zones = [
        _make_zone(zone_id=1, total_time=100, top_score=0.8),
        _make_zone(zone_id=2, total_time=300, top_score=0.6),
    ]
    shortlist = [
        _make_attraction(1, zone_id=1, avg_time_minutes=100, score=0.8),
        _make_attraction(2, zone_id=2, avg_time_minutes=300, score=0.6),
    ]
    surviving, _ = drop_weak_zones(zones, avg_zone_time=200.0, std_deviation=100.0, shortlist=shortlist)
    surviving_ids = {z["zone_id"] for z in surviving}
    assert 1 in surviving_ids
    assert 2 in surviving_ids


def test_drop_zones_drops_below_threshold():
    # threshold = 190 - 110 = 80; zone1.total_time=50 < 80 → DROP (no mustdo)
    zones = [
        _make_zone(zone_id=1, total_time=50,  top_score=0.8),
        _make_zone(zone_id=2, total_time=300, top_score=0.6),
    ]
    shortlist = [
        _make_attraction(1, zone_id=1, avg_time_minutes=50,  score=0.8, is_mustdo=False),
        _make_attraction(2, zone_id=2, avg_time_minutes=300, score=0.6, is_mustdo=False),
    ]
    surviving, _ = drop_weak_zones(zones, avg_zone_time=190.0, std_deviation=110.0, shortlist=shortlist)
    surviving_ids = {z["zone_id"] for z in surviving}
    assert 1 not in surviving_ids
    assert 2 in surviving_ids


def test_drop_zones_mustdo_saves_zone():
    # Same setup as above but zone 1 has a mustdo attraction → zone kept
    zones = [
        _make_zone(zone_id=1, total_time=50,  top_score=0.8),
        _make_zone(zone_id=2, total_time=300, top_score=0.6),
    ]
    shortlist = [
        _make_attraction(1, zone_id=1, avg_time_minutes=50,  score=0.8, is_mustdo=True),
        _make_attraction(2, zone_id=2, avg_time_minutes=300, score=0.6, is_mustdo=False),
    ]
    surviving, _ = drop_weak_zones(zones, avg_zone_time=190.0, std_deviation=110.0, shortlist=shortlist)
    surviving_ids = {z["zone_id"] for z in surviving}
    assert 1 in surviving_ids
    assert 2 in surviving_ids


def test_drop_zones_keeps_mustdo_attractions():
    # Zone 1 would be dropped but contains a mustdo attraction.
    # The mustdo saves the zone (step 2), and the attraction must appear in updated_shortlist.
    zones = [
        _make_zone(zone_id=1, total_time=50,  top_score=0.8),
        _make_zone(zone_id=2, total_time=300, top_score=0.6),
    ]
    shortlist = [
        _make_attraction(10, zone_id=1, avg_time_minutes=50,  score=0.8, is_mustdo=True),
        _make_attraction(20, zone_id=2, avg_time_minutes=300, score=0.6, is_mustdo=False),
    ]
    _, updated_shortlist = drop_weak_zones(zones, avg_zone_time=190.0, std_deviation=110.0, shortlist=shortlist)
    updated_ids = {a["attraction_id"] for a in updated_shortlist}
    assert 10 in updated_ids


def test_drop_zones_zero_sd_drops_nothing():
    # sd=0.0 → threshold = avg - 0 = avg; nothing is strictly less than avg
    # when all zones have the same total_time
    zones = [
        _make_zone(zone_id=1, total_time=200, top_score=0.8),
        _make_zone(zone_id=2, total_time=200, top_score=0.6),
        _make_zone(zone_id=3, total_time=200, top_score=0.5),
    ]
    shortlist = [
        _make_attraction(1, zone_id=1, avg_time_minutes=200, score=0.8),
        _make_attraction(2, zone_id=2, avg_time_minutes=200, score=0.6),
        _make_attraction(3, zone_id=3, avg_time_minutes=200, score=0.5),
    ]
    surviving, updated = drop_weak_zones(zones, avg_zone_time=200.0, std_deviation=0.0, shortlist=shortlist)
    assert len(surviving) == 3
    assert len(updated) == 3


def test_drop_zones_all_would_drop_keeps_best():
    # Artificial avg/sd forces all zones below threshold; no mustdo.
    # Safety: keep the zone with highest top_score.
    zones = [
        _make_zone(zone_id=1, total_time=100, top_score=0.9),
        _make_zone(zone_id=2, total_time=80,  top_score=0.6),
    ]
    shortlist = [
        _make_attraction(1, zone_id=1, avg_time_minutes=100, score=0.9, is_mustdo=False),
        _make_attraction(2, zone_id=2, avg_time_minutes=80,  score=0.6, is_mustdo=False),
    ]
    # avg=500, sd=100 → threshold=400; both zones (100, 80) < 400 → all drop
    surviving, _ = drop_weak_zones(zones, avg_zone_time=500.0, std_deviation=100.0, shortlist=shortlist)
    assert len(surviving) >= 1
    assert surviving[0]["zone_id"] == 1  # highest top_score kept


# ── SECTION 3: distribute_zones_to_days tests ────────────────────────────────

def test_distribute_equal_zones_and_days():
    zones = [
        _make_zone(zone_id=1, total_time=200, top_score=0.9),
        _make_zone(zone_id=2, total_time=180, top_score=0.7),
        _make_zone(zone_id=3, total_time=150, top_score=0.5),
    ]
    result = distribute_zones_to_days(zones, num_days=3)

    assert len(result) == 3
    for day in result:
        assert len(day["zone_ids"]) == 1


def test_distribute_more_zones_than_days():
    zones = [
        _make_zone(zone_id=1, total_time=200, top_score=0.9),
        _make_zone(zone_id=2, total_time=180, top_score=0.7),
        _make_zone(zone_id=3, total_time=150, top_score=0.5),
        _make_zone(zone_id=4, total_time=100, top_score=0.3),
    ]
    result = distribute_zones_to_days(zones, num_days=3)

    assert len(result) == 3
    # One day entry must have two zone_ids (merged)
    multi_zone_days = [d for d in result if len(d["zone_ids"]) > 1]
    assert len(multi_zone_days) >= 1


def test_distribute_fewer_zones_than_days():
    zones = [
        _make_zone(zone_id=1, total_time=300, top_score=0.9),
        _make_zone(zone_id=2, total_time=200, top_score=0.6),
    ]
    result = distribute_zones_to_days(zones, num_days=4)

    assert len(result) == 4
    # At least one zone_id must appear in more than one day's zone_ids
    all_zone_ids = [zid for d in result for zid in d["zone_ids"]]
    duplicates = {zid for zid in all_zone_ids if all_zone_ids.count(zid) > 1}
    assert len(duplicates) >= 1


def test_distribute_sorted_by_day_number():
    zones = [
        _make_zone(zone_id=1, total_time=200, top_score=0.8),
        _make_zone(zone_id=2, total_time=180, top_score=0.6),
        _make_zone(zone_id=3, total_time=150, top_score=0.4),
    ]
    result = distribute_zones_to_days(zones, num_days=3)

    day_numbers = [d["day_number"] for d in result]
    assert day_numbers == sorted(day_numbers)
    assert day_numbers[0] == 1


def test_distribute_all_locked_false():
    zones = [
        _make_zone(zone_id=1, total_time=200, top_score=0.8),
        _make_zone(zone_id=2, total_time=180, top_score=0.6),
    ]
    result = distribute_zones_to_days(zones, num_days=2)

    for day in result:
        assert day["locked"] is False


def test_distribute_empty_zones():
    result = distribute_zones_to_days(surviving_zones=[], num_days=3)

    assert len(result) == 3
    for day in result:
        assert day["zone_ids"] == []
        assert day["locked"] is False


# ── DB functions: integration tests (skipped for now) ────────────────────────
# get_zone_adjacency   — integration test — requires DB
# assign_anchor_zones  — integration test — requires DB
# order_middle_zones   — integration test — requires DB
