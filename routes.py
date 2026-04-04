# routes.py
# All API endpoints.
# Frontend sends requests to these URLs.
# Each route validates input, calls backend logic, returns JSON.

from flask import Blueprint, request, jsonify, session
from database import get_db
from assembly import build_itinerary
import mysql.connector
import json

routes = Blueprint('routes', __name__)


# ============================================================
# HELPER — convert TIME object to minutes from midnight
# ============================================================

def time_to_minutes(t):
    return t.hour * 60 + t.minute


# ============================================================
# ROUTE 1: GET /api/destinations
# Frontend calls this to populate the destination dropdown.
# Returns list of all destinations.
# ============================================================

@routes.route('/api/destinations', methods=['GET'])
def get_destinations():
    """
    No input required.

    Returns:
    {
      "destinations": [
        {"destination_id": 1, "name": "Mahabaleshwar", "state": "Maharashtra"},
        ...
      ]
    }
    """
    db = get_db()
    if not db:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT destination_id, name, state FROM destinations")
        destinations = cursor.fetchall()
        cursor.close()
        return jsonify({"destinations": destinations})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


# ============================================================
# ROUTE 2: GET /api/vibes
# Returns the fixed list of vibe tags for the frontend form.
# ============================================================

@routes.route('/api/vibes', methods=['GET'])
def get_vibes():
    """
    No input required.

    Returns:
    {
      "vibes": ["adventure", "scenic", "cultural", ...]
    }
    """
    vibes = [
        "adventure", "scenic", "cultural", "historical",
        "relaxed", "foodie", "nature", "spiritual", "urban", "offbeat"
    ]
    return jsonify({"vibes": vibes})


# ============================================================
# ROUTE 3: POST /api/trips/create
# Frontend submits the user's trip preferences form here.
# Validates input, stores trip in DB, returns trip_id.
#
# This is the first real action — before the itinerary is built.
# ============================================================

@routes.route('/api/trips/create', methods=['POST'])
def create_trip():
    """
    Frontend sends JSON body:
    {
      "user_id":            1,
      "destination_id":     1,
      "start_date":         "2026-04-10",
      "end_date":           "2026-04-13",
      "num_people":         2,
      "travel_mode":        "car",
      "accommodation_type": "4-star",
      "sleep_hours":        8,
      "meals_per_day":      3,
      "sleep_time":         "22:30",
      "wake_time":          "06:30",
      "priority_order":     ["exploring", "meals", "rest", "sleep"],
      "flexibility":        "moderate",
      "origin_city":        "Pune",
      "arrival_terminal_id":   null,
      "departure_terminal_id": null,
      "vibes": ["scenic", "nature", "adventure"],
      "meal_timings": [
        {"meal_type": "breakfast", "start": 420, "end": 480},
        {"meal_type": "lunch",     "start": 780, "end": 840},
        {"meal_type": "dinner",    "start": 1140, "end": 1200}
      ]
    }

    Returns:
    {
      "trip_id": 1,
      "message": "Trip created successfully"
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    # ── Validate required fields ──
    # Note: `user_id` is derived from session after login, so frontend can omit it.
    required = [
        "destination_id", "start_date", "end_date",
        "num_people", "travel_mode", "accommodation_type",
        "origin_city", "vibes", "priority_order"
    ]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    if len(data.get("vibes", [])) == 0:
        return jsonify({"error": "At least one vibe required"}), 400

    if len(data.get("vibes", [])) > 4:
        return jsonify({"error": "Maximum 4 vibes allowed"}), 400

    db = get_db()
    if not db:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = db.cursor()

        # ── Determine user_id ──
        user_id = data.get("user_id")
        if user_id is None:
            user_id = session.get("user_id")
        if user_id is None:
            return jsonify({"error": "Not logged in"}), 401

        # ── Insert trip row ──
        cursor.execute("""
            INSERT INTO trips (
                user_id, destination_id, start_date, end_date,
                num_people, travel_mode, accommodation_type,
                sleep_hours, meals_per_day, sleep_time, wake_time,
                priority_order, flexibility, origin_city,
                arrival_terminal_id, departure_terminal_id
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """, (
            user_id,
            data["destination_id"],
            data["start_date"],
            data["end_date"],
            data.get("num_people", 1),
            data["travel_mode"],
            data["accommodation_type"],
            data.get("sleep_hours", 8),
            data.get("meals_per_day", 3),
            data.get("sleep_time", "22:00:00"),
            data.get("wake_time", "07:00:00"),
            json.dumps(data["priority_order"]),
            data.get("flexibility", "moderate"),
            data["origin_city"],
            data.get("arrival_terminal_id"),
            data.get("departure_terminal_id")
        ))
        trip_id = cursor.lastrowid

        # ── Insert vibes ──
        for vibe in data["vibes"]:
            cursor.execute(
                "INSERT INTO trip_vibes (trip_id, vibe) VALUES (%s, %s)",
                (trip_id, vibe)
            )

        # ── Insert meal timings ──
        meal_timings = data.get("meal_timings", [])
        if not meal_timings:
            # defaults
            meal_timings = [
                {"meal_type": "breakfast", "start": 420, "end": 480},
                {"meal_type": "lunch",     "start": 780, "end": 840},
                {"meal_type": "dinner",    "start": 1140, "end": 1200}
            ]
        for meal in meal_timings:
            cursor.execute("""
                INSERT INTO trip_meal_timings
                (trip_id, meal_type, preferred_start_minutes, preferred_end_minutes)
                VALUES (%s, %s, %s, %s)
            """, (trip_id, meal["meal_type"], meal["start"], meal["end"]))

        db.commit()
        cursor.close()

        return jsonify({
            "trip_id": trip_id,
            "message": "Trip created successfully"
        }), 201

    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


# ============================================================
# ROUTE 4: POST /api/trips/<trip_id>/generate
# Frontend calls this after creating a trip.
# Runs the full algorithm pipeline and returns the itinerary.
# This is the main algorithm call.
# ============================================================

@routes.route('/api/trips/<int:trip_id>/generate', methods=['POST'])
def generate_itinerary(trip_id):
    """
    No body needed — trip_id is in the URL.

    Returns the complete itinerary:
    {
      "trip_id": 1,
      "destination": "Mahabaleshwar",
      "accommodation": {
        "accommodation_id": 2,
        "name": "Evershine Keys Prima",
        "type": "4-star",
        "zone_id": 1
      },
      "days": [
        {
          "day_number": 1,
          "zone_name": "Venna Lake Area",
          "schedule": [
            {
              "slot_type": "travel",
              "attraction": null,
              "meal_type": null,
              "start_time": "6:30 AM",
              "end_time": "9:30 AM",
              "notes": "travel to destination"
            },
            {
              "slot_type": "attraction",
              "attraction": "Lingmala Waterfall",
              "meal_type": null,
              "start_time": "9:30 AM",
              "end_time": "11:30 AM",
              "notes": "Lingmala Waterfall"
            },
            ...
          ]
        },
        ...
      ]
    }
    """
    db = get_db()
    if not db:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        # verify trip exists
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            "SELECT trip_id FROM trips WHERE trip_id = %s", (trip_id,))
        trip = cursor.fetchone()
        cursor.close()

        if not trip:
            return jsonify({"error": f"Trip {trip_id} not found"}), 404

        # run the full algorithm pipeline
        itinerary = build_itinerary(trip_id, db)

        return jsonify(itinerary), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


# ============================================================
# ROUTE 5: GET /api/trips/<trip_id>/itinerary
# Returns a previously generated itinerary from the DB.
# Frontend uses this to reload a saved plan.
# ============================================================

@routes.route('/api/trips/<int:trip_id>/itinerary', methods=['GET'])
def get_itinerary(trip_id):
    """
    Reads already-written itinerary from DB.
    Does NOT re-run the algorithm.

    Returns same format as /generate.
    """
    db = get_db()
    if not db:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = db.cursor(dictionary=True)

        # get destination name
        cursor.execute("""
            SELECT d.name as destination_name
            FROM trips t
            JOIN destinations d ON t.destination_id = d.destination_id
            WHERE t.trip_id = %s
        """, (trip_id,))
        trip_row = cursor.fetchone()
        if not trip_row:
            return jsonify({"error": "Trip not found"}), 404

        # get accommodation
        cursor.execute("""
            SELECT a.accommodation_id, a.name, a.type, a.zone_id
            FROM accommodation_pick ap
            JOIN accommodations a ON ap.accommodation_id = a.accommodation_id
            WHERE ap.trip_id = %s
        """, (trip_id,))
        accommodation = cursor.fetchone()

        # get days and items
        cursor.execute("""
            SELECT id.day_id, id.day_number, id.zone_id, z.name as zone_name
            FROM itinerary_days id
            JOIN zones z ON id.zone_id = z.zone_id
            WHERE id.trip_id = %s
            ORDER BY id.day_number
        """, (trip_id,))
        days = cursor.fetchall()

        result_days = []
        for day in days:
            cursor.execute("""
                SELECT ii.slot_type, ii.meal_type,
                       ii.start_time, ii.end_time, ii.notes,
                       a.name as attraction_name
                FROM itinerary_items ii
                LEFT JOIN attractions a ON ii.attraction_id = a.attraction_id
                WHERE ii.day_id = %s
                ORDER BY ii.start_time
            """, (day['day_id'],))
            items = cursor.fetchall()

            schedule = []
            for item in items:
                schedule.append({
                    "slot_type":  item['slot_type'],
                    "attraction": item['attraction_name'],
                    "meal_type":  item['meal_type'],
                    "start_time": minutes_to_time_str(item['start_time']),
                    "end_time":   minutes_to_time_str(item['end_time']),
                    "notes":      item['notes']
                })

            result_days.append({
                "day_number": day['day_number'],
                "zone_id":    day['zone_id'],
                "zone_name":  day['zone_name'],
                "schedule":   schedule
            })

        cursor.close()

        return jsonify({
            "trip_id":       trip_id,
            "destination":   trip_row['destination_name'],
            "accommodation": accommodation,
            "days":          result_days
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


# ============================================================
# HELPER — convert minutes from midnight to readable string
# ============================================================

def minutes_to_time_str(minutes):
    hours = minutes // 60
    mins = minutes % 60
    period = 'AM' if hours < 12 else 'PM'
    display_hour = hours if hours <= 12 else hours - 12
    if display_hour == 0:
        display_hour = 12
    return f"{display_hour}:{mins:02d} {period}"
