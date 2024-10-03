import sqlite3
import os

DATABASE_FILE = os.getenv("DATABASE_FILE", "uuid_balance.db")

def init_db():
    connection = sqlite3.connect(DATABASE_FILE)
    cursor = connection.cursor()
    
    # Example table creation, adjust to match your schema
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        uuid TEXT NOT NULL,
        balance INTEGER DEFAULT 0,
        user_agent TEXT
    )
    """)
    
    connection.commit()
    connection.close()
