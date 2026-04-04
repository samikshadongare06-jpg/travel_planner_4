from scoring import score_all_attractions, build_shortlist
from zone_management import (calculate_zone_stats, drop_weak_zones,
                             distribute_zones_to_days)
import mysql.connector

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="password",      # your actual MySQL password
    database="travel_planner"     # your actual DB name
)

user_vibe = ["scenic", "nature", "adventure"]
destination_id = 1
num_days = 3

print("--- STEP 1: Scoring ---")
scored = score_all_attractions(destination_id, user_vibe, db)
print(f"Attractions scored: {len(scored)}")
print(f"Top 3: {[(a['name'], round(a['score'],2)) for a in scored[:3]]}")

print("\n--- STEP 2: Shortlist ---")
shortlist = build_shortlist(scored, 16.0)
print(f"Shortlist length: {len(shortlist)}")
print(f"Total time: {sum(a['avg_time_minutes'] for a in shortlist)} minutes")
print(f"Mustdo included: {[a['name'] for a in shortlist if a['is_mustdo']]}")

print("\n--- STEP 3: Zone Stats ---")
zone_stats, avg, sd = calculate_zone_stats(shortlist)
print(f"Zones found: {len(zone_stats)}")
print(f"Avg zone time: {avg} mins, SD: {sd} mins")
for z in zone_stats:
    print(f"  Zone {z['zone_id']}: {z['total_time']} mins, "
          f"top score {round(z['top_score'],2)}")

print("\n--- STEP 4: Drop Weak Zones ---")
surviving, updated_shortlist = drop_weak_zones(
    zone_stats, avg, sd, shortlist)
print(f"Zones surviving: {len(surviving)}")
print(f"Attractions remaining: {len(updated_shortlist)}")

print("\n--- STEP 5: Distribute to Days ---")
zone_day_map = distribute_zones_to_days(surviving, num_days)
print(f"Days mapped: {len(zone_day_map)}")
for day in zone_day_map:
    print(f"  Day {day['day_number']}: zones {day['zone_ids']}, "
          f"locked={day['locked']}")

db.close()
print("\n--- INTEGRATION COMPLETE ---")
