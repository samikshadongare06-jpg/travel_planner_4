"""
zone_management.py — Group B: Zone Management Functions
Travel Planner backend module.
"""

import math


def calculate_zone_stats(shortlist):
    """
    PURPOSE: Groups shortlisted attractions by zone and computes each zone's total time, attraction count, top score, plus the mean and standard deviation of zone times.
    TIER: 1 (pure)
    IN: shortlist (list[dict]) — output of build_shortlist; each dict has
                                  zone_id, avg_time_minutes, score, is_mustdo
    OUT: tuple —
           [0] zone_stats (list[dict]): one dict per unique zone, sorted by
               top_score descending. Keys: zone_id, total_time,
               attraction_count, top_score
           [1] avg_zone_time (float): mean of total_time across all zones
           [2] std_deviation (float): population std dev of total_time
    CALLS: nothing
    """
    if not shortlist:
        return ([], 0.0, 0.0)

    zones = {}
    for attraction in shortlist:
        zid = attraction.get("zone_id")
        if zid is None:
            # skip attractions with no zone
            continue
        if zid not in zones:
            zones[zid] = {
                "zone_id": zid,
                "total_time": 0,
                "attraction_count": 0,
                "top_score": 0.0,
            }
        zones[zid]["total_time"] += attraction["avg_time_minutes"]
        zones[zid]["attraction_count"] += 1
        if attraction["score"] > zones[zid]["top_score"]:
            zones[zid]["top_score"] = attraction["score"]

    if not zones:
        return ([], 0.0, 0.0)

    zone_list = list(zones.values())
    n = len(zone_list)

    avg = sum(z["total_time"] for z in zone_list) / n
    variance = sum((z["total_time"] - avg) ** 2 for z in zone_list) / n
    sd = math.sqrt(variance)

    zone_list.sort(key=lambda z: z["top_score"], reverse=True)

    return (zone_list, avg, sd)


def get_zone_adjacency(zone_id, db):
    """
    PURPOSE: Fetches the list of zones that are adjacent (neighbouring) to a given zone from the database.
    TIER: 2 (reads DB)
    IN: zone_id (int) — the zone whose neighbours to find
        db            — mysql.connector connection object
    OUT: list[int] — zone_ids of all adjacent zones, sorted ascending;
                     empty list if none found
    CALLS: nothing
    """
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        "SELECT nearby_zone_id FROM zone_nearby WHERE zone_id = %s ORDER BY nearby_zone_id ASC",
        (zone_id,)
    )
    rows = cursor.fetchall()
    cursor.close()

    return [row["nearby_zone_id"] for row in rows]


def drop_weak_zones(zone_stats, avg_zone_time, std_deviation, shortlist):
    """
    PURPOSE: Removes zones whose total attraction time falls below the statistical threshold, while always preserving zones that contain must-do attractions.
    TIER: 1 (pure)
    IN: zone_stats     (list[dict]) — output[0] of calculate_zone_stats
        avg_zone_time  (float)      — output[1] of calculate_zone_stats
        std_deviation  (float)      — output[2] of calculate_zone_stats
        shortlist      (list[dict]) — current shortlist from Group A
    OUT: tuple —
           [0] surviving_zones (list[dict]): zones that passed the drop rule,
               same dict format as zone_stats input, sorted by top_score desc
           [1] updated_shortlist (list[dict]): shortlist with dropped-zone
               attractions removed; is_mustdo attractions always preserved
    CALLS: nothing
    """
    if not shortlist:
        return ([], [])

    # If std_deviation is zero, all zones are equal — nothing is dropped
    if std_deviation == 0.0:
        return (list(zone_stats), list(shortlist))

    threshold = avg_zone_time - std_deviation

    # Find zone_ids that contain at least one mustdo attraction
    mustdo_zone_ids = {a["zone_id"] for a in shortlist if a["is_mustdo"]}

    surviving = []
    dropped_zone_ids = set()

    for zone in zone_stats:
        if zone["total_time"] < threshold and zone["zone_id"] not in mustdo_zone_ids:
            dropped_zone_ids.add(zone["zone_id"])
        else:
            surviving.append(zone)

    # Safety: if all zones would be dropped, keep the one with highest top_score
    if not surviving and zone_stats:
        best = max(zone_stats, key=lambda z: z["top_score"])
        surviving = [best]
        dropped_zone_ids.discard(best["zone_id"])

    surviving_zone_ids = {z["zone_id"] for z in surviving}

    # Build updated shortlist: keep attractions in surviving zones + all mustdo
    updated_shortlist = [
        a for a in shortlist
        if a["zone_id"] in surviving_zone_ids or a["is_mustdo"]
    ]

    return (surviving, updated_shortlist)


def distribute_zones_to_days(surviving_zones, num_days):
    """
    PURPOSE: Distributes surviving zones across trip days by merging (if too many zones) or splitting (if too few), producing an initial zone-to-day map.
    TIER: 1 (pure)
    IN: surviving_zones (list[dict]) — output[0] of drop_weak_zones;
                                        each dict has zone_id, top_score,
                                        total_time, attraction_count
        num_days        (int)         — total number of trip days
    OUT: zone_day_map (list[dict]): one dict per day, sorted by day_number asc.
         Each dict: { day_number (int), zone_ids (list[int]), locked (bool) }
         All locked values are False (set True later by assign_anchor_zones).
    CALLS: nothing
    """
    if num_days == 0:
        return []

    if not surviving_zones:
        return [
            {"day_number": d, "zone_ids": [], "locked": False}
            for d in range(1, num_days + 1)
        ]

    # Build working slots — each zone starts as its own slot
    slots = [
        {
            "zone_ids": [z["zone_id"]],
            "total_time": z["total_time"],
            "top_score": z["top_score"],
        }
        for z in surviving_zones
    ]

    # Case B: more slots than days — merge the two lowest-total_time slots
    while len(slots) > num_days:
        slots.sort(key=lambda s: s["total_time"])
        merged = {
            "zone_ids": slots[0]["zone_ids"] + slots[1]["zone_ids"],
            "total_time": slots[0]["total_time"] + slots[1]["total_time"],
            "top_score": max(slots[0]["top_score"], slots[1]["top_score"]),
        }
        slots = [merged] + slots[2:]

    # Case C: fewer slots than days — split the highest-total_time slot
    while len(slots) < num_days:
        slots.sort(key=lambda s: s["total_time"], reverse=True)
        to_split = slots[0]
        half = to_split["total_time"] // 2
        slot_a = {
            "zone_ids": list(to_split["zone_ids"]),
            "total_time": to_split["total_time"] - half,
            "top_score": to_split["top_score"],
        }
        slot_b = {
            "zone_ids": list(to_split["zone_ids"]),
            "total_time": half,
            "top_score": to_split["top_score"],
        }
        slots = slots[1:] + [slot_a, slot_b]

    # Assign day numbers in top_score descending order
    slots.sort(key=lambda s: s["top_score"], reverse=True)

    result = []
    for i, slot in enumerate(slots):
        result.append({
            "day_number": i + 1,
            "zone_ids": slot["zone_ids"],
            "locked": False,
        })

    result.sort(key=lambda d: d["day_number"])
    return result


def assign_anchor_zones(zone_day_map, arrival_terminal_id, departure_terminal_id, surviving_zones, db):
    """
    PURPOSE: Locks day 1 and the last day to zones determined by the trip's arrival and departure terminals, swapping existing assignments as needed.
    TIER: 2 (reads DB)
    IN: zone_day_map           (list[dict]) — output of distribute_zones_to_days
        arrival_terminal_id    (int|None)   — from trips table; None for car travel
        departure_terminal_id  (int|None)   — from trips table; None for car travel
        surviving_zones        (list[dict]) — for score-based fallback when no terminal
        db                     — mysql.connector connection object
    OUT: list[dict] — same zone_day_map format with day 1 and last day locked=True
                      and their zone_ids set based on terminal proximity
    CALLS: nothing
    """
    if not zone_day_map:
        return zone_day_map

    sorted_zones = sorted(surviving_zones, key=lambda z: z["top_score"], reverse=True)

    def get_terminal_zone(terminal_id):
        """Query terminal_zones for the zone with priority=1 for a terminal."""
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            "SELECT zone_id FROM terminal_zones WHERE terminal_id = %s ORDER BY priority ASC LIMIT 1",
            (terminal_id,)
        )
        row = cursor.fetchone()
        cursor.close()
        return row["zone_id"] if row else None

    def find_day_with_zone(zone_id):
        """Return the day dict that currently holds zone_id, or None."""
        for day in zone_day_map:
            if zone_id in day["zone_ids"]:
                return day
        return None

    def assign_zone_to_day(target_day, zone_id):
        """Place zone_id onto target_day, swapping with its current holder if necessary."""
        existing_day = find_day_with_zone(zone_id)
        if existing_day is not None and existing_day["day_number"] != target_day["day_number"]:
            # Swap: give target_day's current zones to the existing holder
            existing_day["zone_ids"] = list(target_day["zone_ids"])
            target_day["zone_ids"] = [zone_id]
        else:
            # Zone not yet assigned anywhere, or already on target_day
            target_day["zone_ids"] = [zone_id]

    day_1 = zone_day_map[0]
    last_day = zone_day_map[-1]

    # ── Day 1 anchor ──────────────────────────────────────────────────────────
    if arrival_terminal_id is not None:
        arrival_zone = get_terminal_zone(arrival_terminal_id)
        if arrival_zone is None:
            # Terminal exists but has no zone rows — fall back to top-scored zone
            arrival_zone = sorted_zones[0]["zone_id"] if sorted_zones else None
    else:
        # Car travel — use highest scored zone
        arrival_zone = sorted_zones[0]["zone_id"] if sorted_zones else None

    if arrival_zone is not None:
        assign_zone_to_day(day_1, arrival_zone)
    day_1["locked"] = True

    # ── Last day anchor ───────────────────────────────────────────────────────
    if len(zone_day_map) == 1:
        # Single-day trip: day 1 and last day are the same entry
        last_day["locked"] = True
        return zone_day_map

    # Determine which zone is already taken by day 1
    day1_zone = day_1["zone_ids"][0] if day_1["zone_ids"] else None

    if departure_terminal_id is not None:
        departure_zone = get_terminal_zone(departure_terminal_id)
        if departure_zone is None:
            departure_zone = next(
                (z["zone_id"] for z in sorted_zones if z["zone_id"] != day1_zone),
                sorted_zones[0]["zone_id"] if sorted_zones else None,
            )
    else:
        # Car travel — use second highest scored zone (first differs from day 1)
        departure_zone = next(
            (z["zone_id"] for z in sorted_zones if z["zone_id"] != day1_zone),
            sorted_zones[0]["zone_id"] if sorted_zones else None,
        )

    if departure_zone is not None:
        assign_zone_to_day(last_day, departure_zone)
    last_day["locked"] = True

    return zone_day_map


def order_middle_zones(zone_day_map, surviving_zones, db):
    """
    PURPOSE: Re-sequences unlocked middle days so that adjacent zones fall on consecutive days, using a greedy neighbour traversal with a top-score fallback.
    TIER: 2 (reads DB via get_zone_adjacency)
    IN: zone_day_map    (list[dict]) — output of assign_anchor_zones;
                                        day 1 and last day are locked
        surviving_zones (list[dict]) — for score-based fallback ordering
        db              — mysql.connector connection object
    OUT: list[dict] — same zone_day_map format, fully ordered, sorted by
                      day_number ascending; locked days are unchanged
    CALLS: get_zone_adjacency
    """
    if not zone_day_map:
        return zone_day_map

    unlocked_days = [d for d in zone_day_map if not d["locked"]]

    if not unlocked_days:
        return sorted(zone_day_map, key=lambda d: d["day_number"])

    # Collect all zone_ids to assign (preserve duplicates from splits)
    unassigned_zones = []
    for day in unlocked_days:
        for zid in day["zone_ids"]:
            unassigned_zones.append(zid)

    if not unassigned_zones:
        return sorted(zone_day_map, key=lambda d: d["day_number"])

    # Score lookup for fallback: zone_id → top_score
    zone_score_map = {z["zone_id"]: z["top_score"] for z in surviving_zones}

    # Start greedy traversal from day 1's first zone
    day_1 = next((d for d in zone_day_map if d["day_number"] == 1), None)
    current_zone = (day_1["zone_ids"][0] if day_1 and day_1["zone_ids"] else None)

    for day in sorted(unlocked_days, key=lambda d: d["day_number"]):
        if not unassigned_zones:
            break

        assigned = None

        if current_zone is not None:
            neighbours = get_zone_adjacency(current_zone, db)
            for nb in neighbours:
                if nb in unassigned_zones:
                    assigned = nb
                    break

        if assigned is None:
            # Fallback: pick the unassigned zone with the highest top_score
            assigned = max(
                unassigned_zones,
                key=lambda zid: zone_score_map.get(zid, 0.0),
            )

        day["zone_ids"] = [assigned]
        unassigned_zones.remove(assigned)
        current_zone = assigned

    # Any remaining unassigned zones (edge case from merging) go to last unlocked day
    if unassigned_zones:
        last_unlocked = sorted(unlocked_days, key=lambda d: d["day_number"])[-1]
        last_unlocked["zone_ids"].extend(unassigned_zones)

    return sorted(zone_day_map, key=lambda d: d["day_number"])
