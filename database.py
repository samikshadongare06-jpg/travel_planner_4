# database.py
# Manages the MySQL connection for the entire app.
# Every other file imports get_db() from here.
# Never create a connection anywhere else.

import mysql.connector
from mysql.connector import Error

DB_CONFIG = {
    "host":     "localhost",
    "user":     "root",
    "password": "password",    # change this
    "database": "travel_planner"
}

def get_db():
    """
    PURPOSE: Create and return a MySQL connection.
    Call this once per request in routes.py.
    Always close the connection after the request is done.
    """
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        print(f"DB connection error: {e}")
        return None
