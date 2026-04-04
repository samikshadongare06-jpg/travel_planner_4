"""
day_builder.py — Group C: Day Builder Functions
Travel Planner backend module.

All times are integers representing minutes from midnight:
  0 = 12:00am, 360 = 6:00am, 540 = 9:00am, 720 = 12:00pm
  Formula: hours * 60 + minutes
"""


# ── BLOCK DICT FORMAT ─────────────────────────────────────────────────────────
# Every block produced or consumed in this module has exactly:
# {
#   "attraction_id": int or None,
#   "slot_type":     str,   # 'attraction','meal','rest','travel','sleep'
#   "meal_type":     str or None,
#   "start_time":    int,   # minutes from midnight
#   "end_time":      int,
#   "notes":         str or None
# }


# ── PRIORITY MAP: slot_type → priority_order keyword ─────────────────────────
_SLOT_TO_PRIORITY = {
    "attraction": "exploring",
    "meal":       "meals",
    "rest":       "rest",
    "sleep":      "sleep",
    "travel":     "travel",   # handled specially — always wins
}

# ── DEFAULT MEAL TIMINGS (minutes from midnight) ──────────────────────────────
_DEFAULT_MEALS = [
    {"meal_type": "breakfast", "preferred_start_minutes": 420,  "preferred_end_minutes": 480},
    {"meal_type": "lunch",     "preferred_start_minutes": 780,  "preferred_end_minutes": 840},
    {"meal_type": "dinner",    "preferred_start_minutes": 1140, "preferred_end_minutes": 1200},
]


def _make_block(attraction_id, slot_type, meal_type, start_time, end_time, notes):
    """Return a new block dict — never mutates an existing block."""
    return {
        "attraction_id": attraction_id,
        "slot_type":     slot_type,
        "meal_type":     meal_type,
        "start_time":    start_time,
        "end_time":      end_time,
        "notes":         notes,
    }


# ─────────────────────────────────────────────────────────────────────────────
# FUNCTION 1 — get_fixed_blocks
# ─────────────────────────────────────────────────────────────────────────────

def get_fixed_blocks(trip_id, day_number, num_days, db):
    """
    PURPOSE: Builds the immovable time blocks (sleep, meals, travel) for one trip day.
    TIER: 2 (reads DB)
    IN: trip_id    (int)    — trip to fetch settings for
        day_number (int)    — which day of the trip (1-based)
        num_days   (int)    — total number of trip days
        db                  — mysql.connector connection object
    OUT: list[dict] — fixed blocks sorted by start_time ascending,
                      each following the standard block dict format
    CALLS: nothing
    """
    # ── Fetch trip row ────────────────────────────────────────────────────────
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM trips WHERE trip_id = %s", (trip_id,))
    trip = cursor.fetchone()
    cursor.close()

    sleep_time_obj = trip["sleep_time"]
    wake_time_obj  = trip["wake_time"]

    # Convert TIME objects → minutes from midnight
    sleep_start = sleep_time_obj.seconds // 60  # timedelta or datetime.time
    wake_mins   = wake_time_obj.seconds  // 60

    # mysql-connector returns datetime.timedelta for TIME columns
    # .seconds gives total seconds; // 60 gives minutes
    sleep_hours = trip["sleep_hours"]

    blocks = []

    # ── Sleep block ───────────────────────────────────────────────────────────
    blocks.append(_make_block(
        attraction_id=None,
        slot_type="sleep",
        meal_type=None,
        start_time=sleep_start,
        end_time=sleep_start + (sleep_hours * 60),
        notes="sleep",
    ))

    # ── Meal blocks ───────────────────────────────────────────────────────────
    meal_cursor = db.cursor(dictionary=True)
    meal_cursor.execute(
        "SELECT meal_type, preferred_start_minutes, preferred_end_minutes "
        "FROM trip_meal_timings WHERE trip_id = %s",
        (trip_id,)
    )
    meal_rows = meal_cursor.fetchall()
    meal_cursor.close()

    if not meal_rows:
        meal_rows = _DEFAULT_MEALS

    for meal in meal_rows:
        blocks.append(_make_block(
            attraction_id=None,
            slot_type="meal",
            meal_type=meal["meal_type"],
            start_time=meal["preferred_start_minutes"],
            end_time=meal["preferred_end_minutes"],
            notes=meal["meal_type"],
        ))

    # ── Travel block ──────────────────────────────────────────────────────────
    if day_number == 1 or day_number == num_days:
        route_cursor = db.cursor(dictionary=True)
        route_cursor.execute(
            "SELECT avg_hours FROM travel_routes "
            "WHERE origin_city = %s AND destination_id = %s AND travel_mode = %s "
            "LIMIT 1",
            (trip["origin_city"], trip["destination_id"], trip["travel_mode"])
        )
        route = route_cursor.fetchone()
        route_cursor.close()

        travel_minutes = int(float(route["avg_hours"]) * 60) if route else 180

        if day_number == 1:
            blocks.append(_make_block(
                attraction_id=None,
                slot_type="travel",
                meal_type=None,
                start_time=wake_mins,
                end_time=wake_mins + travel_minutes,
                notes="travel to destination",
            ))

        if day_number == num_days and day_number != 1:
            # Return travel: ends at sleep_start, starts travel_minutes before
            blocks.append(_make_block(
                attraction_id=None,
                slot_type="travel",
                meal_type=None,
                start_time=sleep_start - travel_minutes,
                end_time=sleep_start,
                notes="travel back home",
            ))

        # Single-day trip: both arrival and departure
        if day_number == 1 and num_days == 1:
            blocks.append(_make_block(
                attraction_id=None,
                slot_type="travel",
                meal_type=None,
                start_time=sleep_start - travel_minutes,
                end_time=sleep_start,
                notes="travel back home",
            ))

    blocks.sort(key=lambda b: b["start_time"])
    return blocks


# ─────────────────────────────────────────────────────────────────────────────
# FUNCTION 2 — find_food_for_meals
# ─────────────────────────────────────────────────────────────────────────────

def find_food_for_meals(meal_slots, shortlist, zone_id):
    """
    PURPOSE: Attaches a food-capable attraction to each meal slot where one is available in today's zone.
    TIER: 1 (pure)
    IN: meal_slots (list[dict]) — meal blocks from get_fixed_blocks (slot_type='meal')
        shortlist  (list[dict]) — updated_shortlist already filtered to today's zone
        zone_id    (int)        — today's primary zone
    OUT: list[dict] — updated meal_slots with attraction_id and notes set where food found
    CALLS: nothing
    """
    if not shortlist:
        return meal_slots

    # Work on copies — do not mutate inputs
    result_meals = [dict(slot) for slot in meal_slots]
    available = [a for a in shortlist]  # shallow copy for tracking used items

    # Priority order: breakfast first, then lunch, then dinner
    priority = {"breakfast": 0, "lunch": 1, "dinner": 2, "snack": 3}
    result_meals.sort(key=lambda m: priority.get(m.get("meal_type", "snack"), 99))

    used_ids = set()

    for meal in result_meals:
        food_options = [
            a for a in available
            if a["zone_id"] == zone_id
            and a["food_availability"] in ("nearby", "integrated")
            and a["attraction_id"] not in used_ids
        ]

        if food_options:
            best = max(food_options, key=lambda a: a["score"])
            meal["attraction_id"] = best["attraction_id"]
            meal["notes"] = best["name"]
            used_ids.add(best["attraction_id"])

    return result_meals


# ─────────────────────────────────────────────────────────────────────────────
# FUNCTION 3 — resolve_conflict
# ─────────────────────────────────────────────────────────────────────────────

def resolve_conflict(new_block, existing_block, priority_order, is_mustdo, flexibility):
    """
    PURPOSE: Decides which of two overlapping blocks wins its time slot, returning winner and adjusted loser without mutating inputs.
    TIER: 1 (pure)
    IN: new_block      (dict)      — block trying to be placed
        existing_block (dict)      — block already in schedule that overlaps
        priority_order (list[str]) — user's ranked list e.g. ['exploring','meals','rest','sleep']
        is_mustdo      (bool)      — whether new_block's attraction is must-do
        flexibility    (str)       — 'strict' / 'moderate' / 'flexible'
    OUT: dict with keys 'winner' (dict) and 'loser' (dict or None)
    CALLS: nothing
    """
    def _copy(block):
        return dict(block) if block is not None else None

    def _apply_loser(loser_block, winner_block):
        """Shift loser or drop it depending on flexibility."""
        if loser_block is None:
            return None
        if flexibility == "flexible":
            duration = loser_block["end_time"] - loser_block["start_time"]
            shifted = _copy(loser_block)
            shifted["start_time"] = winner_block["end_time"]
            shifted["end_time"]   = winner_block["end_time"] + duration
            return shifted
        # moderate or strict → drop loser
        return None

    # ── RULE 1: mustdo always wins ────────────────────────────────────────────
    if is_mustdo:
        winner = _copy(new_block)
        loser  = _apply_loser(_copy(existing_block), winner)
        return {"winner": winner, "loser": loser}

    # ── RULE 2: travel block always wins (cannot be moved) ────────────────────
    if existing_block["slot_type"] == "travel":
        winner = _copy(existing_block)
        loser  = None  # new block is simply dropped
        return {"winner": winner, "loser": loser}

    # ── RULE 2b: sleep is protected ───────────────────────────────────────────
    if existing_block["slot_type"] == "sleep":
        if flexibility == "flexible":
            # new_block wins; trim sleep by 60 minutes
            winner = _copy(new_block)
            trimmed_sleep = _copy(existing_block)
            trimmed_sleep["end_time"] = existing_block["end_time"] - 60
            return {"winner": winner, "loser": trimmed_sleep}
        else:
            # moderate or strict: existing sleep wins, new_block dropped
            winner = _copy(existing_block)
            return {"winner": winner, "loser": None}

    # ── RULE 3: priority_order for everything else ────────────────────────────
    new_keyword      = _SLOT_TO_PRIORITY.get(new_block["slot_type"], "rest")
    existing_keyword = _SLOT_TO_PRIORITY.get(existing_block["slot_type"], "rest")

    try:
        new_idx      = priority_order.index(new_keyword)
    except ValueError:
        new_idx      = len(priority_order)
    try:
        existing_idx = priority_order.index(existing_keyword)
    except ValueError:
        existing_idx = len(priority_order)

    if new_idx < existing_idx:
        # new_block has higher priority → wins
        winner = _copy(new_block)
        loser  = _apply_loser(_copy(existing_block), winner)
    else:
        # existing wins (equal priority also keeps existing)
        winner = _copy(existing_block)
        loser  = _apply_loser(_copy(new_block), winner)

    return {"winner": winner, "loser": loser}


# ─────────────────────────────────────────────────────────────────────────────
# FUNCTION 4 — anchor_star_attraction
# ─────────────────────────────────────────────────────────────────────────────

def anchor_star_attraction(zone_id, day_schedule, shortlist, priority_order, flexibility):
    """
    PURPOSE: Places the highest-scored attraction for the day's zone into the schedule, resolving any time conflicts via resolve_conflict.
    TIER: 1 (pure)
    IN: zone_id        (int)       — today's zone
        day_schedule   (list[dict])— all blocks placed so far today
        shortlist      (list[dict])— attractions available, filtered to this zone
        priority_order (list[str]) — from trip settings
        flexibility    (str)       — from trip settings
    OUT: tuple — (updated_day_schedule: list[dict], updated_shortlist: list[dict])
    CALLS: resolve_conflict
    """
    # ── Step 1: find star attraction ──────────────────────────────────────────
    zone_attractions = [a for a in shortlist if a["zone_id"] == zone_id]
    if not zone_attractions:
        return (list(day_schedule), list(shortlist))

    star = max(zone_attractions, key=lambda a: a["score"])

    # ── Step 2: determine placement time ──────────────────────────────────────
    recommended = star.get("recommended_time", "anytime")

    # Derive wake_time from schedule: end of sleep block, or min non-sleep start
    wake_time = None
    for block in day_schedule:
        if block["slot_type"] == "sleep":
            wake_time = block["end_time"]
            break
    if wake_time is None:
        non_sleep = [b for b in day_schedule if b["slot_type"] != "sleep"]
        wake_time = min((b["start_time"] for b in non_sleep), default=540)

    if recommended == "morning":
        preferred_start = wake_time
    elif recommended == "evening":
        preferred_start = 1020  # 5 PM
    else:
        # "anytime" — find first empty slot after wake_time
        occupied = sorted(
            [(b["start_time"], b["end_time"]) for b in day_schedule],
            key=lambda t: t[0],
        )
        preferred_start = wake_time
        for (s, e) in occupied:
            if s <= preferred_start < e:
                preferred_start = e  # push past this occupied block

    if preferred_start is None:
        preferred_start = 540

    preferred_end = preferred_start + star["avg_time_minutes"]

    # ── Step 3: check for conflicts ───────────────────────────────────────────
    new_block = _make_block(
        attraction_id=star["attraction_id"],
        slot_type="attraction",
        meal_type=None,
        start_time=preferred_start,
        end_time=preferred_end,
        notes=star["name"],
    )

    schedule = list(day_schedule)

    conflicting = next(
        (b for b in schedule
         if b["start_time"] < preferred_end and b["end_time"] > preferred_start),
        None,
    )

    if conflicting:
        result = resolve_conflict(
            new_block, conflicting, priority_order, star["is_mustdo"], flexibility
        )
        schedule.remove(conflicting)
        schedule.append(result["winner"])
        if result["loser"] is not None:
            schedule.append(result["loser"])
    else:
        schedule.append(new_block)

    # ── Strenuous + immediate meal: add 45 min buffer ─────────────────────────
    if star["is_strenuous"] and flexibility != "strict":
        for block in schedule:
            if (block["slot_type"] == "meal"
                    and block["start_time"] == preferred_end):
                block["start_time"] += 45
                block["end_time"]   += 45

    # ── Step 5: remove star from shortlist ────────────────────────────────────
    updated_shortlist = [
        a for a in shortlist if a["attraction_id"] != star["attraction_id"]
    ]

    # ── Step 6: sort and return ───────────────────────────────────────────────
    schedule.sort(key=lambda b: b["start_time"])
    return (schedule, updated_shortlist)


# ─────────────────────────────────────────────────────────────────────────────
# FUNCTION 5 — merge_empty_slots
# ─────────────────────────────────────────────────────────────────────────────

def merge_empty_slots(day_schedule, wake_time, sleep_start):
    """
    PURPOSE: Scans the day schedule and returns a list of merged empty time windows between wake and sleep.
    TIER: 1 (pure)
    IN: day_schedule (list[dict]) — all placed blocks for the day
        wake_time    (int)        — start of usable day (minutes from midnight)
        sleep_start  (int)        — end of usable day (minutes from midnight)
    OUT: list[dict] — empty windows sorted by start_time ascending, each with
                      start_time (int), end_time (int), duration_minutes (int)
    CALLS: nothing
    """
    if not day_schedule:
        duration = sleep_start - wake_time
        if duration > 0:
            return [{"start_time": wake_time, "end_time": sleep_start,
                     "duration_minutes": duration}]
        return []

    # ── Step 1: build merged occupied intervals ───────────────────────────────
    raw = sorted(
        [(b["start_time"], b["end_time"]) for b in day_schedule],
        key=lambda t: t[0],
    )

    merged_occupied = []
    for (s, e) in raw:
        if merged_occupied and s <= merged_occupied[-1][1]:
            # overlapping or adjacent — extend
            merged_occupied[-1] = (merged_occupied[-1][0], max(merged_occupied[-1][1], e))
        else:
            merged_occupied.append((s, e))

    # ── Step 2–4: find gaps between occupied intervals within [wake, sleep] ───
    windows = []
    cursor_pos = wake_time

    for (occ_start, occ_end) in merged_occupied:
        gap_end = min(occ_start, sleep_start)
        if gap_end > cursor_pos:
            duration = gap_end - cursor_pos
            if duration > 0:
                windows.append({
                    "start_time":       cursor_pos,
                    "end_time":         gap_end,
                    "duration_minutes": duration,
                })
        cursor_pos = max(cursor_pos, min(occ_end, sleep_start))

    # Trailing gap after last occupied block
    if cursor_pos < sleep_start:
        duration = sleep_start - cursor_pos
        if duration > 0:
            windows.append({
                "start_time":       cursor_pos,
                "end_time":         sleep_start,
                "duration_minutes": duration,
            })

    # ── Step 5: filter zero-duration windows ──────────────────────────────────
    windows = [w for w in windows if w["duration_minutes"] > 0]
    windows.sort(key=lambda w: w["start_time"])
    return windows


# ─────────────────────────────────────────────────────────────────────────────
# FUNCTION 6 — fill_remaining_slots
# ─────────────────────────────────────────────────────────────────────────────

def fill_remaining_slots(empty_windows, shortlist, user_preference):
    """
    PURPOSE: Fills empty time windows with the best-fitting attractions from the shortlist, marking leftover time as rest.
    TIER: 1 (pure)
    IN: empty_windows   (list[dict]) — output of merge_empty_slots
        shortlist       (list[dict]) — remaining unscheduled attractions for today's zone
        user_preference (str)        — 'efficient' (strict/moderate) or 'relaxed' (flexible)
    OUT: tuple — ([0] new_blocks: list[dict], [1] updated_shortlist: list[dict])
    CALLS: nothing
    """
    if not empty_windows:
        return ([], list(shortlist))

    remaining = list(shortlist)
    new_blocks = []
    used_ids = set()

    for window in empty_windows:
        duration = window["duration_minutes"]
        w_start  = window["start_time"]

        if duration <= 120:
            # Too small for a meaningful attraction — rest block regardless of preference
            new_blocks.append(_make_block(
                attraction_id=None,
                slot_type="rest",
                meal_type=None,
                start_time=w_start,
                end_time=window["end_time"],
                notes="rest",
            ))
            continue

        # duration > 120 — try to fit an attraction
        candidates = [
            a for a in remaining
            if a["avg_time_minutes"] <= duration
            and a["attraction_id"] not in used_ids
        ]

        if candidates:
            best = max(candidates, key=lambda a: a["score"])
            attr_end = w_start + best["avg_time_minutes"]

            new_blocks.append(_make_block(
                attraction_id=best["attraction_id"],
                slot_type="attraction",
                meal_type=None,
                start_time=w_start,
                end_time=attr_end,
                notes=best["name"],
            ))
            used_ids.add(best["attraction_id"])
            remaining = [a for a in remaining if a["attraction_id"] != best["attraction_id"]]

            # Remaining time after attraction → rest block
            leftover = window["end_time"] - attr_end
            if leftover > 0:
                new_blocks.append(_make_block(
                    attraction_id=None,
                    slot_type="rest",
                    meal_type=None,
                    start_time=attr_end,
                    end_time=window["end_time"],
                    notes="rest",
                ))
        else:
            # No fitting attraction → full window becomes rest
            new_blocks.append(_make_block(
                attraction_id=None,
                slot_type="rest",
                meal_type=None,
                start_time=w_start,
                end_time=window["end_time"],
                notes="rest",
            ))

    return (new_blocks, remaining)
