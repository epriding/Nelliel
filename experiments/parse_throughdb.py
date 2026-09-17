import sqlite3
import pandas as pd
import os

db_path = '/mnt/chromeos/removable/USB Drive/market_data.db'

if os.path.exists(db_path):
    try:
        conn = sqlite3.connect(db_path)

    except sqlite3.Error as e:
        print("Error connecting to SQLite database:", e)

    else:
        print("Connected to SQLite database successfully.")

        df = pd.read_sql_query("SELECT * FROM market_data", conn)

        df.head()

else:
    print(f"Database file not found at {db_path}. Please check the path and try again.")