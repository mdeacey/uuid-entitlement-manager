import os
import sqlite3
from dotenv import load_dotenv
from shared.utils.logging import logger

# Load environment variables
load_dotenv()

DATABASE_FILE = os.getenv("DATABASE_FILE", "uuid_balance.db")

def init_db():
    """
    Initialize the shared SQLite database.
    Creates the 'users', 'purchase_packs', and 'coupons' tables if they do not exist.
    """
    logger.info("Initializing shared database: '{}'...", DATABASE_FILE)
    try:
        with sqlite3.connect(DATABASE_FILE) as conn:
            c = conn.cursor()
            # Create users table
            c.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    uuid TEXT PRIMARY KEY,
                    user_agent TEXT,
                    balance INTEGER,
                    last_awarded INTEGER
                )
            ''')
            # Create purchase packs table
            c.execute('''
                CREATE TABLE IF NOT EXISTS purchase_packs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pack_name TEXT UNIQUE,
                    original_name TEXT,
                    size INTEGER,
                    price REAL,
                    currency TEXT
                )
            ''')
            # Create coupons table
            c.execute('''
                CREATE TABLE IF NOT EXISTS coupons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    coupon_code TEXT UNIQUE,
                    discount INTEGER,
                    applicable_packs TEXT
                )
            ''')
    except sqlite3.Error as e:
        logger.exception("Shared database initialization error: {}", e)
