"""
test_integration_cd.py
Tests Group C day builder with real data from Groups A and B
Run with: python test_integration_cd.py
"""

from scoring import score_all_attractions, build_shortlist
from zone_management import (calculate_zone_stats, drop_weak_zones,
                              distribute_zones_to_days, assign_anchor_zones,
                              order_middle_zones)
from day_builder import (get_fixed_blocks, find_food_for_meals,
                         anchor_star_attraction, merge_empty_slots,
                         fill_remaining_slots)
import mysql.connector
import json

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="password",       # change this
    database="travel_planner"
)

trip_id = 1
destination_id = 1
user_vibe = ["scenic", "nature", "adventure"]
num_days = 3

print("=" * 50)
print("GROUP C INTEGRATION TEST")
print("=" * 50)

# ── Rebuild shortlist and zone map from A and B ──
print("\n[Setup] Running Groups A and B to get inputs for C...")
scored = score_all_attractions(destination_id, user_vibe, db)
shortlist = build_shortlist(scored, 16.0)
zone_stats, avg, sd = calculate_zone_stats(shortlist)
surviving, updated_shortlist = drop_weak_zones(zone_stats, avg, sd, shortlist)
zone_day_map = distribute_zones_to_days(surviving, num_days)

# fetch terminal ids from DB for this trip
cursor = db.cursor(dictionary=True)
cursor.execute("SELECT * FROM trips WHERE trip_id = %s", (trip_id,))
trip = cursor.fetchone()
cursor.close()

zone_day_map = assign_anchor_zones(
    zone_day_map,
    trip['arrival_terminal_id'],
    trip['departure_terminal_id'],
    surviving,
    db
)
zone_day_map = order_middle_zones(zone_day_map, surviving, db)

print(f"Zone day map ready: {len(zone_day_map)} days")
print(f"Shortlist for C: {len(updated_shortlist)} attractions")

# ── Test get_fixed_blocks for each day ──
print("\n--- STEP 1: get_fixed_blocks ---")


wake_td = trip['wake_time']
wake_time_mins = wake_td.seconds // 60
# wake_time_mins = trip['wake_time'].hour * 60 + trip['wake_time'].minute

sleep_td = trip['sleep_time']
sleep_start_mins = sleep_td.seconds // 60
# sleep_start_mins = trip['sleep_time'].hour * 60 + trip['sleep_time'].minute

for day_entry in zone_day_map:
    day_num = day_entry['day_number']
    fixed = get_fixed_blocks(trip_id, day_num, num_days, db)
    print(f"\n  Day {day_num} fixed blocks ({len(fixed)} total):")
    for block in fixed:
        start_h = block['start_time'] // 60
        start_m = block['start_time'] % 60
        end_h = block['end_time'] // 60
        end_m = block['end_time'] % 60
        print(f"    {block['slot_type']:12} "
              f"{start_h:02d}:{start_m:02d} → {end_h:02d}:{end_m:02d}"
              f"  {block.get('notes','')}")

    meal_slots = [b for b in fixed if b['slot_type'] == 'meal']
    print(f"  Meal slots found: {len(meal_slots)}")

# ── Test one full day build ──
print("\n--- STEP 2: Full day build for Day 1 ---")

day_entry = zone_day_map[0]
zone_id = day_entry['zone_ids'][0]
today_shortlist = [a for a in updated_shortlist
                   if a['zone_id'] in day_entry['zone_ids']]

print(f"  Zone: {zone_id}")
print(f"  Attractions available: {len(today_shortlist)}")

fixed = get_fixed_blocks(trip_id, 1, num_days, db)
meal_slots = [b for b in fixed if b['slot_type'] == 'meal']
updated_meals = find_food_for_meals(meal_slots, today_shortlist, zone_id)

food_attached = sum(1 for m in updated_meals if m['attraction_id'] is not None)
print(f"\n  find_food_for_meals:")
print(f"  Meals with food attraction: {food_attached}/{len(meal_slots)}")

day_schedule = fixed.copy()
for i, block in enumerate(day_schedule):
    if block['slot_type'] == 'meal':
        for updated in updated_meals:
            if block['meal_type'] == updated['meal_type']:
                day_schedule[i] = updated

priority_order = json.loads(trip['priority_order'])
flexibility = trip['flexibility']

day_schedule, today_shortlist = anchor_star_attraction(
    zone_id, day_schedule, today_shortlist, priority_order, flexibility)

anchored = [b for b in day_schedule if b['slot_type'] == 'attraction']
print(f"\n  anchor_star_attraction:")
print(f"  Anchored attractions: {len(anchored)}")
for b in anchored:
    start_h = b['start_time'] // 60
    start_m = b['start_time'] % 60
    print(f"    {b.get('notes','?'):30} at {start_h:02d}:{start_m:02d}")

empty_windows = merge_empty_slots(day_schedule, wake_time_mins, sleep_start_mins)
print(f"\n  merge_empty_slots:")
print(f"  Empty windows: {len(empty_windows)}")
for w in empty_windows:
    print(f"    {w['duration_minutes']} mins free "
          f"({w['start_time']//60:02d}:{w['start_time']%60:02d} → "
          f"{w['end_time']//60:02d}:{w['end_time']%60:02d})")

user_preference = 'relaxed' if flexibility == 'flexible' else 'efficient'
new_blocks, today_shortlist = fill_remaining_slots(
    empty_windows, today_shortlist, user_preference)

print(f"\n  fill_remaining_slots:")
print(f"  New blocks added: {len(new_blocks)}")
for b in new_blocks:
    start_h = b['start_time'] // 60
    start_m = b['start_time'] % 60
    print(f"    {b['slot_type']:12} at {start_h:02d}:{start_m:02d} "
          f"— {b.get('notes','')}")

final_schedule = sorted(day_schedule + new_blocks,
                        key=lambda x: x['start_time'])
print(f"\n  FINAL Day 1 schedule ({len(final_schedule)} blocks):")
for b in final_schedule:
    start_h = b['start_time'] // 60
    start_m = b['start_time'] % 60
    end_h = b['end_time'] // 60
    end_m = b['end_time'] % 60
    print(f"    {b['slot_type']:12} "
          f"{start_h:02d}:{start_m:02d} → {end_h:02d}:{end_m:02d}"
          f"  {b.get('notes','')}")

db.close()
print("\n--- GROUP C INTEGRATION COMPLETE ---")
