from flask import Blueprint, jsonify, request, session

from database import get_db
from backend.budgeting import estimate_trip_budget


trip_extras_routes = Blueprint("trip_extras_routes", __name__)


def _require_login():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return int(user_id)


@trip_extras_routes.route("/api/me/trips", methods=["GET"])
def list_my_trips():
    user_id = _require_login()
    if user_id is None:
        return jsonify({"error": "Not logged in"}), 401

    db = get_db()
    if not db:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cur = db.cursor(dictionary=True)
        cur.execute(
            """
            SELECT
              t.trip_id,
              t.destination_id,
              d.name as destination_name,
              t.start_date,
              t.end_date,
              t.num_people,
              t.travel_mode,
              t.accommodation_type,
              (SELECT COUNT(*) FROM saved_trip_plans sp WHERE sp.trip_id = t.trip_id) AS is_saved,
              (SELECT COUNT(*)
                 FROM itinerary_days id
                 WHERE id.trip_id = t.trip_id
              ) AS itinerary_days_count
            FROM trips t
            JOIN destinations d ON t.destination_id = d.destination_id
            WHERE t.user_id = %s
            ORDER BY t.created_at DESC
            """,
            (user_id,),
        )
        rows = cur.fetchall()
        cur.close()

        trips = []
        for r in rows:
            if (r.get("is_saved") or 0) <= 0:
                continue
            trips.append({
                "trip_id": r["trip_id"],
                "destination_id": r["destination_id"],
                "destination_name": r["destination_name"],
                "start_date": str(r["start_date"]),
                "end_date": str(r["end_date"]),
                "num_people": r["num_people"],
                "travel_mode": r["travel_mode"],
                "accommodation_type": r["accommodation_type"],
                "itinerary_ready": (r["itinerary_days_count"] or 0) > 0,
            })

        return jsonify({"trips": trips}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@trip_extras_routes.route("/api/trips/<int:trip_id>/zone-doodles", methods=["GET"])
def zone_doodles(trip_id: int):
    """
    Returns a mapping from zone_id -> primary tag.
    The UI uses the tag to render a doodle (no images stored in DB).
    """
    db = get_db()
    if not db:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cur = db.cursor(dictionary=True)

        cur.execute(
            "SELECT DISTINCT zone_id FROM itinerary_days WHERE trip_id = %s",
            (trip_id,),
        )
        zone_rows = cur.fetchall()
        zone_ids = [r["zone_id"] for r in zone_rows if r["zone_id"] is not None]

        if not zone_ids:
            return jsonify({"zone_doodles": []}), 200

        placeholders = ", ".join(["%s"] * len(zone_ids))
        cur.execute(
            f"""
            SELECT a.zone_id, at.tag, COUNT(*) AS cnt
            FROM attractions a
            JOIN attraction_tags at ON a.attraction_id = at.attraction_id
            WHERE a.zone_id IN ({placeholders})
            GROUP BY a.zone_id, at.tag
            """,
            tuple(zone_ids),
        )
        tag_rows = cur.fetchall()
        cur.close()

        # pick the most frequent tag per zone
        by_zone = {}
        for row in tag_rows:
            zid = row["zone_id"]
            tag = row["tag"]
            cnt = int(row["cnt"] or 0)
            if zid not in by_zone or cnt > by_zone[zid]["cnt"]:
                by_zone[zid] = {"tag": tag, "cnt": cnt}

        zone_doodles = [
            {"zone_id": zid, "primary_tag": by_zone[zid]["tag"]}
            for zid in zone_ids
            if zid in by_zone
        ]
        return jsonify({"zone_doodles": zone_doodles}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@trip_extras_routes.route("/api/trips/<int:trip_id>/budget", methods=["GET"])
def trip_budget(trip_id: int):
    db = get_db()
    if not db:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cur = db.cursor(dictionary=True)
        cur.execute(
            """
            SELECT
              trip_id,
              user_id,
              destination_id,
              start_date,
              end_date,
              num_people,
              travel_mode,
              accommodation_type,
              meals_per_day
            FROM trips
            WHERE trip_id = %s
            """,
            (trip_id,),
        )
        trip_row = cur.fetchone()
        cur.close()

        if not trip_row:
            return jsonify({"error": "Trip not found"}), 404

        estimate = estimate_trip_budget(trip_row)
        return jsonify(estimate), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@trip_extras_routes.route("/api/trips/<int:trip_id>/save", methods=["POST"])
def save_trip_plan(trip_id: int):
    user_id = _require_login()
    if user_id is None:
        return jsonify({"error": "Not logged in"}), 401

    db = get_db()
    if not db:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cur = db.cursor(dictionary=True)
        cur.execute(
            "SELECT trip_id, user_id FROM trips WHERE trip_id = %s",
            (trip_id,),
        )
        row = cur.fetchone()
        if not row:
            cur.close()
            return jsonify({"error": "Trip not found"}), 404
        if int(row["user_id"]) != int(user_id):
            cur.close()
            return jsonify({"error": "Forbidden"}), 403

        # idempotent save
        cur2 = db.cursor()
        cur2.execute(
            "INSERT IGNORE INTO saved_trip_plans (trip_id) VALUES (%s)",
            (trip_id,),
        )
        db.commit()
        cur.close()
        cur2.close()

        return jsonify({"message": "Saved"}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

