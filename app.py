# app.py
# Entry point. Run this file to start the backend server.
# Run with: python app.py
# Server starts at http://localhost:5000

import os
from flask import Flask
from flask_cors import CORS
from routes import routes
from backend.api.auth_routes import auth_routes
from backend.api.trip_extras_routes import trip_extras_routes

app = Flask(__name__)

# Allow frontend (running on a different port) to talk to this backend
CORS(app)

# Register all routes
app.register_blueprint(routes)
app.register_blueprint(auth_routes)
app.register_blueprint(trip_extras_routes)

# Session cookie key (dev-only)
app.secret_key = "dev-change-me"


@app.route("/")
def index():
    # Minimal UI served by Flask from /static
    return app.send_static_file("index.html")

if __name__ == '__main__':
    port = int(os.environ.get("PORT", "5001"))
    app.run(debug=True, port=port)


# ============================================================
# INSTALL REQUIREMENTS BEFORE RUNNING:
# pip install flask flask-cors mysql-connector-python
#
# YOUR FOLDER STRUCTURE SHOULD NOW LOOK LIKE:
#
# travel_planner/
#   app.py                    ← start the server with this
#   routes.py                 ← API endpoints
#   database.py               ← DB connection
#   assembly.py               ← Group D (orchestrator)
#   day_builder.py            ← Group C
#   zone_management.py        ← Group B
#   scoring.py                ← Group A
#   schema.sql                ← DB schema
#   sample_data.sql           ← seed data
#
# ============================================================
