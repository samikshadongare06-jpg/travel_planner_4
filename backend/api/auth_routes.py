from flask import Blueprint, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from database import get_db


auth_routes = Blueprint("auth_routes", __name__)


@auth_routes.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or "@" not in email:
        return jsonify({"error": "Valid email required"}), 400
    if len(password) < 4:
        return jsonify({"error": "Password too short"}), 400

    db = get_db()
    if not db:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cur = db.cursor(dictionary=True)
        cur.execute("SELECT user_id FROM users WHERE email = %s", (email,))
        if cur.fetchone() is not None:
            return jsonify({"error": "Email already registered"}), 409

        password_hash = generate_password_hash(password)
        cur.execute(
            "INSERT INTO users (email, password_hash) VALUES (%s, %s)",
            (email, password_hash),
        )
        user_id = cur.lastrowid
        db.commit()
        cur.close()

        session["user_id"] = user_id
        session["email"] = email

        return jsonify({"user_id": user_id, "email": email}), 201
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@auth_routes.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    db = get_db()
    if not db:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cur = db.cursor(dictionary=True)
        cur.execute(
            "SELECT user_id, email, password_hash FROM users WHERE email = %s",
            (email,),
        )
        row = cur.fetchone()
        cur.close()

        if row is None:
            return jsonify({"error": "Invalid credentials"}), 401

        stored_hash = row["password_hash"]
        ok = False

        # Normal path for users created via register()
        try:
            ok = check_password_hash(stored_hash, password)
        except Exception:
            ok = False

        # Dev fallback (so your existing seed user can log in)
        if not ok and stored_hash == password:
            ok = True

        if not ok:
            return jsonify({"error": "Invalid credentials"}), 401

        session["user_id"] = row["user_id"]
        session["email"] = row.get("email")

        return jsonify({"user_id": row["user_id"], "email": row.get("email")}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@auth_routes.route("/api/auth/me", methods=["GET"])
def me():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"user_id": None}), 200

    return jsonify({"user_id": user_id, "email": session.get("email")}), 200


@auth_routes.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out"}), 200

