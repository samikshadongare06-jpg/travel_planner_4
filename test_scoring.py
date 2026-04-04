"""
test_scoring.py — Unit tests for scoring.py
Run with: pytest test_scoring.py
Note: score_all_attractions is tested separately as an integration test (requires DB).
"""

import pytest
from scoring import calculate_jaccard, score_attraction, build_shortlist


# ── SECTION 1: calculate_jaccard tests ──

def test_jaccard_identical_sets():
    result = calculate_jaccard(["scenic", "nature"], ["scenic", "nature"])
    assert result == 1.0


def test_jaccard_no_overlap():
    result = calculate_jaccard(["scenic", "nature"], ["cultural", "historical"])
    assert result == 0.0


def test_jaccard_partial_overlap():
    result = calculate_jaccard(
        ["scenic", "nature", "adventure"],
        ["scenic", "adventure", "cultural"]
    )
    assert result == pytest.approx(0.5)


def test_jaccard_empty_both():
    result = calculate_jaccard([], [])
    assert result == 0.0


def test_jaccard_one_empty():
    result = calculate_jaccard(["scenic"], [])
    assert result == 0.0


def test_jaccard_case_insensitive():
    result = calculate_jaccard(["Scenic", "NATURE"], ["scenic", "nature"])
    assert result == 1.0


def test_jaccard_duplicates_ignored():
    result = calculate_jaccard(["scenic", "scenic", "nature"], ["scenic", "nature"])
    assert result == 1.0


# ── SECTION 2: score_attraction tests ──

def test_score_perfect_match_high_rating_new_tags():
    attraction = {"rating": 5.0, "tags": ["scenic"]}
    result = score_attraction(attraction, ["scenic"], [])
    assert result == pytest.approx(1.0)


def test_score_no_match_low_rating_no_diversity():
    attraction = {"rating": 1.0, "tags": ["cultural"]}
    result = score_attraction(attraction, ["scenic"], ["cultural"])
    # jaccard=0.0, normalized=0.2, diversity=0
    assert result == pytest.approx(0.06)


def test_score_rating_clamp_above_max():
    attraction = {"rating": 6.0, "tags": ["scenic"]}
    result = score_attraction(attraction, ["scenic"], [])
    # rating clamped to 5.0 → same as perfect match
    assert result == pytest.approx(1.0)


def test_score_rating_clamp_below_min():
    attraction = {"rating": 0.0, "tags": ["scenic"]}
    result = score_attraction(attraction, ["scenic"], [])
    # rating clamped to 1.0, normalized=0.2; jaccard=1.0, diversity=1
    assert result == pytest.approx(0.76)


def test_score_diversity_bonus_triggers():
    attraction = {"rating": 3.0, "tags": ["offbeat"]}
    result = score_attraction(attraction, [], ["scenic", "nature"])
    # jaccard=0.0, normalized=0.6, diversity=1
    assert result == pytest.approx(0.28)


def test_score_no_diversity_bonus():
    attraction = {"rating": 3.0, "tags": ["scenic"]}
    result = score_attraction(attraction, [], ["scenic", "nature"])
    # jaccard=0.0, normalized=0.6, diversity=0
    assert result == pytest.approx(0.18)


# ── SECTION 3: build_shortlist tests ──
# note: score_all_attractions is tested separately
#       as an integration test (requires DB)

def _make_attraction(attraction_id, avg_time_minutes, is_mustdo, score):
    """Helper to build a minimal attraction dict for shortlist tests."""
    return {
        "attraction_id":    attraction_id,
        "name":             f"Attraction {attraction_id}",
        "score":            score,
        "avg_time_minutes": avg_time_minutes,
        "is_mustdo":        is_mustdo,
        "is_strenuous":     False,
        "food_availability": "none",
        "zone_id":          1,
        "tags":             [],
    }


def test_shortlist_fills_to_lower_bound():
    # total=480 min, lower=300, upper=660
    attractions = [
        _make_attraction(1, 120, False, 0.9),
        _make_attraction(2, 120, False, 0.8),
        _make_attraction(3, 120, False, 0.7),
        _make_attraction(4, 120, False, 0.6),
    ]
    result = build_shortlist(attractions, 8)
    # After 3rd: accumulated=360 >= 300 → stop
    assert len(result) == 3


def test_shortlist_mustdo_never_dropped():
    # total=60 min, lower=-120 (already negative, so lower_bound is below 0)
    attractions = [
        _make_attraction(1, 300, True,  0.5),
        _make_attraction(2, 300, False, 0.9),
    ]
    result = build_shortlist(attractions, 1)
    attraction_ids = [a["attraction_id"] for a in result]
    assert 1 in attraction_ids  # mustdo is always present


def test_shortlist_empty_input():
    result = build_shortlist([], 10)
    assert result == []


def test_shortlist_mustdo_added_in_second_pass():
    # total=240 min, lower=60, upper=420
    attractions = [
        _make_attraction(1, 180, False, 0.9),  # high score, not mustdo
        _make_attraction(2, 180, True,  0.3),  # low score, mustdo
    ]
    result = build_shortlist(attractions, 4)
    # First pass stops after attraction 1 (180 >= 60)
    # Second pass: attraction 2 is mustdo and missing → add it
    result_ids = [a["attraction_id"] for a in result]
    assert 1 in result_ids
    assert 2 in result_ids


def test_shortlist_preserves_score_order():
    attractions = [
        _make_attraction(1, 60, False, 0.9),
        _make_attraction(2, 60, False, 0.7),
        _make_attraction(3, 60, False, 0.5),
    ]
    result = build_shortlist(attractions, 10)
    scores = [a["score"] for a in result]
    assert scores == sorted(scores, reverse=True)
