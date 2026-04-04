"""
test_integration_abcd.py

Full pipeline: A → B → C → D
Uses trip_id=1 from sample data.
Writes itinerary to DB.
Prints complete readable itinerary.
"""

from assembly import build_itinerary
import mysql.connector

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="password",       # change this
    database="travel_planner"
)

print("=" * 60)
print("FULL PIPELINE TEST — A → B → C → D")
print("=" * 60)

trip_id = 1

print(f"\nBuilding itinerary for trip_id={trip_id}...")
print("(This runs the entire algorithm pipeline)\n")

result = build_itinerary(trip_id, db)

print(f"Destination: {result['destination']}")
print(f"Total days:  {len(result['days'])}")
print(f"Accommodation: {result['accommodation']['name'] if result['accommodation'] else 'None'}")

print("\n" + "=" * 60)
print("COMPLETE ITINERARY")
print("=" * 60)

for day in result['days']:
    print(f"\n── Day {day['day_number']}: {day['zone_name']} ──")
    for item in day['schedule']:
        label = item['attraction'] or item['slot_type']
        meal = f" ({item['meal_type']})" if item['meal_type'] else ""
        print(f"  {item['start_time']:>8} → {item['end_time']:>8}  "
              f"{item['slot_type']:12}  {label}{meal}")

print("\n" + "=" * 60)
print("WHAT TO CHECK:")
print("=" * 60)
print(f"  Days in output:        {len(result['days'])} (expect 3)")
print(f"  Days in DB:")

cursor = db.cursor()
cursor.execute("SELECT COUNT(*) FROM itinerary_days WHERE trip_id=%s",
               (trip_id,))
db_days = cursor.fetchone()[0]
print(f"    itinerary_days rows: {db_days} (expect 3)")

cursor.execute("""
    SELECT COUNT(*) FROM itinerary_items ii
    JOIN itinerary_days id ON ii.day_id = id.day_id
    WHERE id.trip_id = %s
""", (trip_id,))
db_items = cursor.fetchone()[0]
print(f"    itinerary_items rows: {db_items} (expect >10)")

cursor.execute("SELECT COUNT(*) FROM accommodation_pick WHERE trip_id=%s",
               (trip_id,))
db_acc = cursor.fetchone()[0]
print(f"    accommodation_pick:  {db_acc} (expect 1)")
cursor.close()

attractions_in_plan = sum(
    1 for day in result['days']
    for item in day['schedule']
    if item['slot_type'] == 'attraction'
)
print(f"\n  Attractions scheduled: {attractions_in_plan}")

mustdo_names = ['Panchgani Tablelands', 'Lingmala Waterfall',
                'Wilson Point (Sunrise)', 'Pratapgad Fort']
scheduled_names = [
    item['attraction']
    for day in result['days']
    for item in day['schedule']
    if item['attraction']
]
print(f"  Must-do attractions included:")
for name in mustdo_names:
    found = name in scheduled_names
    print(f"    {'✓' if found else '✗'} {name}")

db.close()

print("\n" + "=" * 60)
if db_days == 3 and db_items > 10 and db_acc == 1:
    print("PIPELINE STATUS: ALL CHECKS PASSED")
    print("Your backend is complete.")
else:
    print("PIPELINE STATUS: SOME CHECKS FAILED")
    print("Paste output above and debug before moving to frontend.")
print("=" * 60)
