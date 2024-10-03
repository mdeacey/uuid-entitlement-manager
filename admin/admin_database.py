import os
import sqlite3
from dotenv import load_dotenv
from shared.utils.logging import logger

# Load environment variables
load_dotenv(dotenv_path="./admin/admin.env")

# Admin-specific database file path from environment
DB_FILE = os.getenv('ADMIN_DATABASE_FILE', 'admin_uuid_balance.db')

def init_db():
    """
    Initialize the SQLite database for admin.
    Creates the 'users' table if it does not exist.
    """
    logger.info("Initializing admin database: '{}'...", DB_FILE)
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    uuid TEXT PRIMARY KEY,
                    user_agent TEXT,
                    balance INTEGER,
                    last_awarded INTEGER
                )
            ''')
    except sqlite3.Error as e:
        logger.exception("Admin database initialization error: {}", e)

def clear_all_balances():
    """
    Clears all balances to zero for all users.
    """
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute('UPDATE users SET balance = 0')
            logger.info("All user balances have been cleared to zero.")
    except sqlite3.Error as e:
        logger.exception("Admin database error while clearing all balances: {}", e)

def delete_all_user_records():
    """
    Deletes all user records from the admin database.
    """
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute('DELETE FROM users')
            logger.info("All user records have been successfully deleted from the admin database.")
    except sqlite3.Error as e:
        logger.exception("Admin database error while deleting all user records: {}", e)
