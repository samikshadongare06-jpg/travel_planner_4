"""
scoring.py — Group A: Scoring Functions
Travel Planner backend module.
"""


def calculate_jaccard(set_a, set_b):
    """
    PURPOSE: Calculates Jaccard similarity between two lists of vibe tags.
    TIER: 1 (pure)
    IN: set_a (list of str) — first set of tags
        set_b (list of str) — second set of tags
    OUT: float — Jaccard similarity score between 0.0 and 1.0
    CALLS: nothing
    """
    a = {tag.lower() for tag in set_a}
    b = {tag.lower() for tag in set_b}

    if not a and not b:
        return 0.0

    intersection = a & b
    union = a | b

    return len(intersection) / len(union)


def score_attraction(attraction, user_vibe, already_shortlisted_tags):
    """
    PURPOSE: Computes the final score for a single attraction based on vibe match, rating, and diversity.
    TIER: 1 (pure)
    IN: attraction (dict) — must contain 'rating' (float) and 'tags' (list[str])
        user_vibe (list[str]) — vibe tags from the user's trip
        already_shortlisted_tags (list[str]) — all tags accumulated from attractions already shortlisted
    OUT: float — final score between 0.0 and 1.0
    CALLS: calculate_jaccard
    """
    rating = attraction["rating"]
    tags = attraction["tags"]

    # Clamp rating to valid range
    if rating < 1.0:
        rating = 1.0
    elif rating > 5.0:
        rating = 5.0

    normalized_rating = float(rating) / 5.0

    jaccard = calculate_jaccard(tags, user_vibe)

    # Diversity bonus: 1 if attraction adds at least one new tag
    shortlisted_set = {tag.lower() for tag in already_shortlisted_tags}
    attraction_tag_set = {tag.lower() for tag in tags}
    diversity_bonus = 1 if attraction_tag_set - shortlisted_set else 0

    score = (jaccard * 0.6) + (normalized_rating * 0.3) + (diversity_bonus * 0.1)
    return score


def score_all_attractions(destination_id, user_vibe, db):
    """
    PURPOSE: Fetches all attractions for a destination from the DB, scores each one, and returns them sorted by score descending.
    TIER: 2 (reads DB)
    IN: destination_id (int) — which destination to score attractions for
        user_vibe (list[str]) — vibe tags from the user's trip
        db — mysql.connector connection object
    OUT: list of dicts sorted by score descending, each with keys:
         attraction_id, name, score, avg_time_minutes, is_mustdo,
         is_strenuous, food_availability, zone_id, tags
    CALLS: score_attraction
    """
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM attractions WHERE destination_id = %s",
        (destination_id,)
    )
    attractions = cursor.fetchall()
    cursor.close()

    if not attractions:
        return []

    already_shortlisted_tags = []
    results = []

    for row in attractions:
        # Fetch tags for this attraction
        tag_cursor = db.cursor(dictionary=True)
        tag_cursor.execute(
            "SELECT tag FROM attraction_tags WHERE attraction_id = %s",
            (row["attraction_id"],)
        )
        tag_rows = tag_cursor.fetchall()
        tag_cursor.close()

        tags = [t["tag"] for t in tag_rows] if tag_rows else []

        attraction_dict = {
            "rating": row["rating"],
            "tags": tags,
        }

        score = score_attraction(attraction_dict, user_vibe, already_shortlisted_tags)

        # Extend running tag list AFTER scoring
        already_shortlisted_tags.extend(tags)

        results.append({
            "attraction_id":    int(row["attraction_id"]),
            "name":             row["name"],
            "score":            score,
            "avg_time_minutes": int(row["avg_time_minutes"]),
            "is_mustdo":        bool(row["is_mustdo"]),
            "is_strenuous":     bool(row["is_strenuous"]),
            "food_availability": row["food_availability"],
            "zone_id":          int(row["zone_id"]),
            "tags":             tags,
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results


def build_shortlist(scored_attractions, total_trip_hours):
    """
    PURPOSE: Trims the scored attractions list down to a shortlist that fits within the trip's available time, always preserving must-do attractions.
    TIER: 1 (pure)
    IN: scored_attractions (list[dict]) — output of score_all_attractions, sorted by score descending
        total_trip_hours (float) — total available trip hours across all days
    OUT: list[dict] — shortlisted attractions in score-descending order, always including all must-do attractions
    CALLS: nothing
    """
    if not scored_attractions:
        return []

    total_trip_minutes = total_trip_hours * 60
    lower_bound = total_trip_minutes - 180

    # If total_trip_hours is 0 or negative, return only mustdo attractions
    if total_trip_hours <= 0:
        return [a for a in scored_attractions if a["is_mustdo"]]

    shortlist = []
    accumulated_minutes = 0
    stop = False

    for attraction in scored_attractions:
        if stop:
            # Still add if mustdo
            if attraction["is_mustdo"]:
                shortlist.append(attraction)
            continue

        shortlist.append(attraction)
        accumulated_minutes += attraction["avg_time_minutes"]

        if accumulated_minutes >= lower_bound:
            stop = True

    # Second pass: ensure all mustdo attractions are included
    shortlist_ids = {a["attraction_id"] for a in shortlist}
    for attraction in scored_attractions:
        if attraction["is_mustdo"] and attraction["attraction_id"] not in shortlist_ids:
            shortlist.append(attraction)
            shortlist_ids.add(attraction["attraction_id"])

    # Preserve score-descending order
    shortlist.sort(key=lambda x: x["score"], reverse=True)
    return shortlist
