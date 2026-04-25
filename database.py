# database.py
# Manages the MySQL connection for the entire app.
# Every other file imports get_db() from here.
# Never create a connection anywhere else.

# import mysql.connector
# from mysql.connector import Error

# DB_CONFIG = {
#     "host":     "localhost",
#     "user":     "root",
#     "password": "password",    # change this
#     "database": "travel_planner"
# }

# def get_db():
#     """
#     PURPOSE: Create and return a MySQL connection.
#     Call this once per request in routes.py.
#     Always close the connection after the request is done.
#     """
#     try:
#         connection = mysql.connector.connect(**DB_CONFIG)
#         return connection
#     except Error as e:
#         print(f"DB connection error: {e}")
#         return None


# import mysql.connector
# from mysql.connector import Error
# import os

# DB_CONFIG = {
#     "host":     os.environ.get("DB_HOST", "localhost"),
#     "user":     os.environ.get("DB_USER", "root"),
#     "password": os.environ.get("DB_PASSWORD", ""),
#     "database": os.environ.get("DB_NAME", "travel_planner")
# }

# def get_db():
#     """
#     PURPOSE: Create and return a MySQL connection.
#     Call this once per request in routes.py.
#     Always close the connection after the request is done.
#     """
#     try:
#         connection = mysql.connector.connect(**DB_CONFIG)
#         return connection
#     except Error as e:
#         print(f"DB connection error: {e}")
#         return None
    

import mysql.connector
from mysql.connector import Error
import os

def get_db():
    """
    PURPOSE: Create and return a MySQL connection.
    Call this once per request in routes.py.
    Always close the connection after the request is done.
    """
    try:
        database_url = os.environ.get("DATABASE_URL")
        
        # Parse the URL: mysql://user:password@host:port/dbname
        from urllib.parse import urlparse
        url = urlparse(database_url)
        
        connection = mysql.connector.connect(
            host=url.hostname,
            user=url.username,
            password=url.password,
            database=url.path[1:],  # removes the leading /
            port=url.port
        )
        return connection
    except Error as e:
        print(f"DB connection error: {e}")
        return None