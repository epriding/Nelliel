import sqlite3
import os

db_path = r'/mnt/chromeos/removable/USB Drive/market_data.db'

if os.path.exists(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Query to get the table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        if tables:
            print("Tables in the database:")
            for table in tables:
                print(table[0])
        else:
            print("No tables found in the database.")

    except sqlite3.Error as e:
        print("Error connecting to SQLite database:", e)

    finally:
        if conn:
            conn.close()