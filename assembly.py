"""
assembly.py — Group D: Final Assembly Functions
Travel Planner backend module.

This module orchestrates Groups A, B, and C in sequence,
writes the final itinerary to the database, and returns
a complete, frontend-ready output dict.
"""

import json
from datetime import date

from scoring import score_all_attractions, build_shortlist
from zone_management import (
    calculate_zone_stats,
    drop_weak_zones,
    distribute_zones_to_days,
    assign_anchor_zones,
    order_middle_zones,
)
from day_builder import (
    get_fixed_blocks,
    find_food_for_meals,
    anchor_star_attraction,
    merge_empty_slots,
    fill_remaining_slots,
)


# ─────────────────────────────────────────────────────────────────────────────
# FUNCTION 1 — calculate_available_hours
# ─────────────────────────────────────────────────────────────────────────────

def calculate_available_hours(trip_id, db):
    """
    PURPOSE: Calculates total usable trip hours after subtracting sleep, meals, and travel time from each day.
    TIER: 2 (reads DB)
    IN: trip_id (int) — trip to calculate hours for
        db            — mysql.connector connection object
    OUT: dict with keys: total_days, usable_hours_per_day, day1_available_hours,
                          lastday_available_hours, total_trip_hours (all floats/ints)
    CALLS: nothing
    """
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM trips WHERE trip_id = %s", (trip_id,))
    trip = cursor.fetchone()
    cursor.close()

    # ── Step 1: total days ────────────────────────────────────────────────────
    start = trip["start_date"]
    end   = trip["end_date"]
    if isinstance(start, str):
        from datetime import datetime
        start = datetime.strptime(start, "%Y-%m-%d").date()
        end   = datetime.strptime(end,   "%Y-%m-%d").date()

    total_days = max((end - start).days, 1)

    # ── Step 2: usable hours per day ──────────────────────────────────────────
    avg_meal_duration   = 0.75  # 45 minutes per meal (hardcoded per spec)
    meals_time          = trip["meals_per_day"] * avg_meal_duration
    usable_hours_per_day = 24.0 - trip["sleep_hours"] - meals_time

    # ── Step 3: fetch travel hours ────────────────────────────────────────────
    route_cursor = db.cursor(dictionary=True)
    route_cursor.execute(
        "SELECT avg_hours FROM travel_routes "
        "WHERE origin_city = %s AND destination_id = %s AND travel_mode = %s "
        "LIMIT 1",
        (trip["origin_city"], trip["destination_id"], trip["travel_mode"])
    )
    route = route_cursor.fetchone()
    route_cursor.close()

    travel_hours = float(route["avg_hours"]) if route else 3.0

    # ── Step 4: per-day adjustments ───────────────────────────────────────────
    if total_days == 1:
        day1_available_hours    = usable_hours_per_day - (travel_hours * 2)
        lastday_available_hours = day1_available_hours
    else:
        day1_available_hours    = usable_hours_per_day - travel_hours
        lastday_available_hours = usable_hours_per_day - travel_hours

    # ── Step 5: total trip hours ──────────────────────────────────────────────
    if total_days == 1:
        total_trip_hours = day1_available_hours
    else:
        middle_days      = total_days - 2
        total_trip_hours = (
            day1_available_hours
            + lastday_available_hours
            + (middle_days * usable_hours_per_day)
        )

    # ── Step 6: floor at 0.0; minimum 1.0 for total ──────────────────────────
    day1_available_hours    = max(day1_available_hours,    0.0)
    lastday_available_hours = max(lastday_available_hours, 0.0)
    usable_hours_per_day    = max(usable_hours_per_day,    0.0)
    total_trip_hours        = max(total_trip_hours,        1.0)

    return {
        "total_days":              total_days,
        "usable_hours_per_day":    usable_hours_per_day,
        "day1_available_hours":    day1_available_hours,
        "lastday_available_hours": lastday_available_hours,
        "total_trip_hours":        total_trip_hours,
    }


# ─────────────────────────────────────────────────────────────────────────────
# FUNCTION 2 — select_accommodation
# ─────────────────────────────────────────────────────────────────────────────

def select_accommodation(trip_id, db):
    """
    PURPOSE: Picks the best matching accommodation for the trip, preferring the central zone and the user's type preference.
    TIER: 2 (reads DB)
    IN: trip_id (int) — trip whose accommodation_type and destination to use
        db            — mysql.connector connection object
    OUT: dict with keys: accommodation_id, name, type, zone_id — or None if not found
    CALLS: nothing
    """
    # ── Step 1: fetch trip ────────────────────────────────────────────────────
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM trips WHERE trip_id = %s", (trip_id,))
    trip = cursor.fetchone()
    cursor.close()

    # ── Step 2: fetch matching accommodations ─────────────────────────────────
    acc_cursor = db.cursor(dictionary=True)
    acc_cursor.execute(
        "SELECT accommodation_id, name, type, zone_id "
        "FROM accommodations "
        "WHERE destination_id = %s AND type = %s AND max_capacity >= %s",
        (trip["destination_id"], trip["accommodation_type"], trip["num_people"])
    )
    results = acc_cursor.fetchall()
    acc_cursor.close()

    # Relax type constraint if nothing matched
    if not results:
        fallback_cursor = db.cursor(dictionary=True)
        fallback_cursor.execute(
            "SELECT accommodation_id, name, type, zone_id "
            "FROM accommodations WHERE destination_id = %s",
            (trip["destination_id"],)
        )
        results = fallback_cursor.fetchall()
        fallback_cursor.close()

    if not results:
        return None

    # ── Step 3: prefer central zone ───────────────────────────────────────────
    dest_cursor = db.cursor(dictionary=True)
    dest_cursor.execute(
        "SELECT central_zone_id FROM destinations WHERE destination_id = %s",
        (trip["destination_id"],)
    )
    dest = dest_cursor.fetchone()
    dest_cursor.close()

    central_zone_id = dest["central_zone_id"] if dest else None

    if central_zone_id:
        central_match = next(
            (r for r in results if r["zone_id"] == central_zone_id), None
        )
        if central_match:
            return central_match

    return results[0]


# ─────────────────────────────────────────────────────────────────────────────
# FUNCTION 3 — run_scoring_pipeline
# ─────────────────────────────────────────────────────────────────────────────

def run_scoring_pipeline(trip_id, db):
    """
    PURPOSE: Runs the full Group A scoring sequence — hours calculation, attraction scoring, and shortlist building.
    TIER: 2 (reads DB)
    IN: trip_id (int) — trip to score attractions for
        db            — mysql.connector connection object
    OUT: dict with keys: shortlist (list[dict]), total_trip_hours (float)
    CALLS: calculate_available_hours, score_all_attractions, build_shortlist
    """
    # ── Step 1: available hours ───────────────────────────────────────────────
    hours_result    = calculate_available_hours(trip_id, db)
    total_trip_hours = hours_result["total_trip_hours"]

    # ── Step 2: fetch destination and vibes ───────────────────────────────────
    trip_cursor = db.cursor(dictionary=True)
    trip_cursor.execute(
        "SELECT destination_id FROM trips WHERE trip_id = %s", (trip_id,)
    )
    trip = trip_cursor.fetchone()
    trip_cursor.close()

    vibe_cursor = db.cursor(dictionary=True)
    vibe_cursor.execute(
        "SELECT vibe FROM trip_vibes WHERE trip_id = %s", (trip_id,)
    )
    vibe_rows = vibe_cursor.fetchall()
    vibe_cursor.close()

    user_vibe      = [row["vibe"] for row in vibe_rows]
    destination_id = trip["destination_id"]

    # ── Step 3 & 4: score and shortlist ──────────────────────────────────────
    scored    = score_all_attractions(destination_id, user_vibe, db)
    shortlist = build_shortlist(scored, total_trip_hours)

    return {"shortlist": shortlist, "total_trip_hours": total_trip_hours}


# ─────────────────────────────────────────────────────────────────────────────
# FUNCTION 4 — run_zone_pipeline
# ─────────────────────────────────────────────────────────────────────────────

def run_zone_pipeline(trip_id, shortlist, db):
    """
    PURPOSE: Runs the full Group B zone management sequence — stats, dropping, distributing, anchoring, and ordering zones across days.
    TIER: 2 (reads DB)
    IN: trip_id   (int)       — trip to derive day count and terminal ids from
        shortlist (list[dict])— from run_scoring_pipeline
        db                    — mysql.connector connection object
    OUT: dict with keys: zone_day_map (list[dict]), updated_shortlist (list[dict])
    CALLS: calculate_zone_stats, drop_weak_zones, distribute_zones_to_days,
           assign_anchor_zones, order_middle_zones
    """
    # ── Step 1: fetch trip metadata ───────────────────────────────────────────
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM trips WHERE trip_id = %s", (trip_id,))
    trip = cursor.fetchone()
    cursor.close()

    start = trip["start_date"]
    end   = trip["end_date"]
    if isinstance(start, str):
        from datetime import datetime
        start = datetime.strptime(start, "%Y-%m-%d").date()
        end   = datetime.strptime(end,   "%Y-%m-%d").date()

    num_days              = max((end - start).days, 1)
    arrival_terminal_id   = trip["arrival_terminal_id"]
    departure_terminal_id = trip["departure_terminal_id"]

    # ── Step 2: zone stats ────────────────────────────────────────────────────
    zone_stats, avg, sd = calculate_zone_stats(shortlist)

    # ── Step 3: drop weak zones ───────────────────────────────────────────────
    surviving_zones, updated_shortlist = drop_weak_zones(zone_stats, avg, sd, shortlist)

    # ── Step 4: distribute ────────────────────────────────────────────────────
    zone_day_map = distribute_zones_to_days(surviving_zones, num_days)

    # ── Step 5: anchor day 1 and last day ─────────────────────────────────────
    zone_day_map = assign_anchor_zones(
        zone_day_map, arrival_terminal_id, departure_terminal_id,
        surviving_zones, db
    )

    # ── Step 6: order middle days ─────────────────────────────────────────────
    zone_day_map = order_middle_zones(zone_day_map, surviving_zones, db)

    return {
        "zone_day_map":      zone_day_map,
        "updated_shortlist": updated_shortlist,
    }


# ─────────────────────────────────────────────────────────────────────────────
# FUNCTION 5 — run_day_builder
# ─────────────────────────────────────────────────────────────────────────────

def run_day_builder(trip_id, zone_day_map, updated_shortlist, db):
    """
    PURPOSE: Runs the full Group C day builder for every day in the zone map, producing a complete schedule per day.
    TIER: 2 (reads DB via get_fixed_blocks)
    IN: trip_id           (int)       — trip to fetch settings from
        zone_day_map      (list[dict])— from run_zone_pipeline
        updated_shortlist (list[dict])— from run_zone_pipeline
        db                            — mysql.connector connection object
    OUT: list[dict] — one dict per day with keys: day_number, zone_ids, schedule
    CALLS: get_fixed_blocks, find_food_for_meals, anchor_star_attraction,
           merge_empty_slots, fill_remaining_slots
    """
    # ── Fetch trip settings once ──────────────────────────────────────────────
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM trips WHERE trip_id = %s", (trip_id,))
    trip = cursor.fetchone()
    cursor.close()

    wake_time_obj  = trip["wake_time"]
    sleep_time_obj = trip["sleep_time"]
    wake_time_mins  = wake_time_obj.seconds  // 60
    sleep_start_mins = sleep_time_obj.seconds // 60

    priority_order = json.loads(trip["priority_order"]) if isinstance(trip["priority_order"], str) else trip["priority_order"]
    flexibility    = trip["flexibility"]

    start = trip["start_date"]
    end   = trip["end_date"]
    if isinstance(start, str):
        from datetime import datetime
        start = datetime.strptime(start, "%Y-%m-%d").date()
        end   = datetime.strptime(end,   "%Y-%m-%d").date()

    num_days = max((end - start).days, 1)

    user_preference = "relaxed" if flexibility == "flexible" else "efficient"

    all_days         = []
    remaining_short  = list(updated_shortlist)  # shared pool across days

    for day_entry in sorted(zone_day_map, key=lambda d: d["day_number"]):
        day_number    = day_entry["day_number"]
        zone_ids      = day_entry["zone_ids"]
        primary_zone  = zone_ids[0] if zone_ids else None

        # Filter shortlist to today's zones
        today_shortlist = [
            a for a in remaining_short if a["zone_id"] in zone_ids
        ] if zone_ids else []

        # ── Step 1: fixed blocks ──────────────────────────────────────────────
        fixed = get_fixed_blocks(trip_id, day_number, num_days, db)

        # ── Step 2: find food for meals ───────────────────────────────────────
        if primary_zone is not None:
            meal_slots    = [b for b in fixed if b["slot_type"] == "meal"]
            updated_meals = find_food_for_meals(meal_slots, today_shortlist, primary_zone)

            # Replace meal blocks in fixed with updated versions
            meal_idx = 0
            fixed_updated = []
            for b in fixed:
                if b["slot_type"] == "meal" and meal_idx < len(updated_meals):
                    fixed_updated.append(updated_meals[meal_idx])
                    meal_idx += 1
                else:
                    fixed_updated.append(b)
            fixed = fixed_updated

            # IMPORTANT: if a food attraction got attached to a meal slot,
            # remove it from today's attraction pool so it doesn't get scheduled again
            # by the star anchor or slot filling.
            used_food_ids = {
                m.get("attraction_id")
                for m in updated_meals
                if m.get("attraction_id") is not None
            }
            if used_food_ids:
                today_shortlist = [
                    a for a in today_shortlist
                    if a.get("attraction_id") not in used_food_ids
                ]

        # ── Step 3: anchor star attraction ────────────────────────────────────
        if primary_zone is not None and today_shortlist:
            day_schedule, today_shortlist = anchor_star_attraction(
                primary_zone, fixed, today_shortlist, priority_order, flexibility
            )
        else:
            day_schedule = list(fixed)

        # ── Step 4: merge empty slots ─────────────────────────────────────────
        empty_windows = merge_empty_slots(day_schedule, wake_time_mins, sleep_start_mins)

        # ── Step 5: fill remaining slots ──────────────────────────────────────
        new_blocks, today_shortlist = fill_remaining_slots(
            empty_windows, today_shortlist, user_preference
        )
        day_schedule.extend(new_blocks)

        # ── Step 6: finalize day ──────────────────────────────────────────────
        day_schedule.sort(key=lambda b: b["start_time"])

        # Remove used attractions from the shared pool
        used_ids = {
            b["attraction_id"] for b in day_schedule
            if b["attraction_id"] is not None
        }
        remaining_short = [
            a for a in remaining_short if a["attraction_id"] not in used_ids
        ]

        all_days.append({
            "day_number": day_number,
            "zone_ids":   zone_ids,
            "schedule":   day_schedule,
        })

    return all_days


# ─────────────────────────────────────────────────────────────────────────────
# HELPER — minutes_to_readable
# ─────────────────────────────────────────────────────────────────────────────

def _minutes_to_readable(minutes):
    """Convert integer minutes-from-midnight to a readable time string like '9:00 AM'."""
    hours      = minutes // 60
    mins       = minutes % 60
    period     = "AM" if hours < 12 else "PM"
    display_hr = hours if hours <= 12 else hours - 12
    if display_hr == 0:
        display_hr = 12
    return f"{display_hr}:{mins:02d} {period}"


# ─────────────────────────────────────────────────────────────────────────────
# FUNCTION 6 — build_itinerary
# ─────────────────────────────────────────────────────────────────────────────

def build_itinerary(trip_id, db):
    """
    PURPOSE: Orchestrates all pipeline stages, writes the complete itinerary to the database, and returns a frontend-ready output dict.
    TIER: 3 (reads and writes DB)
    IN: trip_id (int) — trip to build the itinerary for
        db            — mysql.connector connection object
    OUT: dict with keys: trip_id, destination, days (list), accommodation (dict or None)
    CALLS: run_scoring_pipeline, run_zone_pipeline, run_day_builder,
           select_accommodation
    """
    # ── Step 1: scoring pipeline ──────────────────────────────────────────────
    scoring_result   = run_scoring_pipeline(trip_id, db)
    shortlist        = scoring_result["shortlist"]

    # ── Step 2: zone pipeline ─────────────────────────────────────────────────
    zone_result      = run_zone_pipeline(trip_id, shortlist, db)
    zone_day_map     = zone_result["zone_day_map"]
    updated_shortlist = zone_result["updated_shortlist"]

    # ── Step 3: day builder ───────────────────────────────────────────────────
    all_days = run_day_builder(trip_id, zone_day_map, updated_shortlist, db)

    # ── Step 4: accommodation ─────────────────────────────────────────────────
    accommodation = select_accommodation(trip_id, db)

    # ── Step 5: write itinerary_days and itinerary_items ─────────────────────
    write_cursor = db.cursor()

    # Delete any existing itinerary for this trip so re-runs are idempotent.
    # itinerary_items must be deleted first (foreign key on day_id).
    write_cursor.execute(
        "DELETE FROM itinerary_items WHERE day_id IN "
        "(SELECT day_id FROM itinerary_days WHERE trip_id = %s)",
        (trip_id,)
    )
    write_cursor.execute(
        "DELETE FROM itinerary_days WHERE trip_id = %s",
        (trip_id,)
    )

    for day in all_days:
        primary_zone = day["zone_ids"][0] if day["zone_ids"] else None

        try:
            write_cursor.execute(
                "INSERT INTO itinerary_days (trip_id, day_number, zone_id) "
                "VALUES (%s, %s, %s)",
                (trip_id, day["day_number"], primary_zone)
            )
            day_id = write_cursor.lastrowid
        except Exception as e:
            day_id = None
            day["_write_error"] = str(e)

        if day_id is None:
            continue

        for block in day["schedule"]:
            try:
                write_cursor.execute(
                    "INSERT INTO itinerary_items "
                    "(day_id, attraction_id, slot_type, meal_type, "
                    "start_time, end_time, notes) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (
                        day_id,
                        block["attraction_id"],
                        block["slot_type"],
                        block["meal_type"],
                        block["start_time"],
                        block["end_time"],
                        block["notes"],
                    )
                )
            except Exception as e:
                # Do not crash — log error as note and continue
                block["notes"] = f"[write_error: {e}]"

    # ── Step 6: write accommodation pick ─────────────────────────────────────
    if accommodation is not None:
        try:
            write_cursor.execute(
                "INSERT IGNORE INTO accommodation_pick "
                "(trip_id, accommodation_id) VALUES (%s, %s)",
                (trip_id, accommodation["accommodation_id"])
            )
        except Exception:
            pass

    # ── Step 7: single commit ─────────────────────────────────────────────────
    db.commit()
    write_cursor.close()

    # ── Step 8: build output dict ─────────────────────────────────────────────
    # Fetch destination name
    dest_cursor = db.cursor(dictionary=True)
    dest_cursor.execute(
        "SELECT d.name AS dest_name "
        "FROM trips t JOIN destinations d ON t.destination_id = d.destination_id "
        "WHERE t.trip_id = %s",
        (trip_id,)
    )
    dest_row = dest_cursor.fetchone()
    dest_cursor.close()
    destination_name = dest_row["dest_name"] if dest_row else "Unknown"

    # Fetch zone names in one query for all zone_ids we'll need
    all_zone_ids = list({
        zid
        for day in all_days
        for zid in day["zone_ids"]
        if zid is not None
    })

    zone_name_map = {}
    if all_zone_ids:
        placeholders = ", ".join(["%s"] * len(all_zone_ids))
        zone_cursor = db.cursor(dictionary=True)
        zone_cursor.execute(
            f"SELECT zone_id, name FROM zones WHERE zone_id IN ({placeholders})",
            tuple(all_zone_ids)
        )
        for row in zone_cursor.fetchall():
            zone_name_map[row["zone_id"]] = row["name"]
        zone_cursor.close()

    # Build readable days
    output_days = []
    for day in all_days:
        primary_zone = day["zone_ids"][0] if day["zone_ids"] else None
        zone_name    = zone_name_map.get(primary_zone, "Unknown Zone")

        schedule_items = []
        for block in day["schedule"]:
            # Resolve attraction name
            attraction_name = None
            if block["attraction_id"] is not None:
                attraction_name = block["notes"]  # set to attraction name during build

            schedule_items.append({
                "slot_type":  block["slot_type"],
                "attraction": attraction_name,
                "meal_type":  block["meal_type"],
                "start_time": _minutes_to_readable(block["start_time"]),
                "end_time":   _minutes_to_readable(block["end_time"]),
                "notes":      block["notes"],
            })

        output_days.append({
            "day_number": day["day_number"],
            "zone_id": primary_zone,
            "zone_name":  zone_name,
            "schedule":   schedule_items,
        })

    return {
        "trip_id":       trip_id,
        "destination":   destination_name,
        "days":          output_days,
        "accommodation": accommodation,
    }
