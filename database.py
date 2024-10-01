import os
import sqlite3
import logging
import time
import uuid
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get the database file from the environment
DB_FILE = os.getenv('DATABASE_FILE')
logging.info(f"Using database file: {DB_FILE}")
logging.info(f"Running in Flask environment: {os.getenv('FLASK_ENV')}")

def init_db():
    """Initializes the database and creates tables if they do not exist."""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                uuid TEXT PRIMARY KEY, 
                user_agent TEXT,
                balance INTEGER,
                last_awarded INTEGER
            )
        ''')
        conn.commit()
        logging.info("Database initialized successfully.")
    except sqlite3.Error as e:
        logging.error(f"Database initialization error: {e}")
    finally:
        conn.close()

def generate_uuid(user_agent, starting_balance=10):
    """Generates a new UUID for a user, adds them to the database, and returns the UUID."""
    user_uuid = str(uuid.uuid4())
    add_user(user_uuid, user_agent, starting_balance)
    return user_uuid

def add_user(user_uuid, user_agent, starting_balance):
    """Adds a new user to the database."""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('INSERT INTO users (uuid, user_agent, balance, last_awarded) VALUES (?, ?, ?, ?)', 
                  (user_uuid, user_agent, starting_balance, int(time.time())))
        conn.commit()
        logging.info(f"User {user_uuid} added successfully.")
    except sqlite3.Error as e:
        logging.error(f"Database error while adding user: {e}")
    finally:
        conn.close()

def get_balance(user_uuid):
    """Retrieves the balance of a user."""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('SELECT balance FROM users WHERE uuid = ?', (user_uuid,))
        result = c.fetchone()
        return result[0] if result else 0
    except sqlite3.Error as e:
        logging.error(f"Database error while retrieving balance for user {user_uuid}: {e}")
        return 0
    finally:
        conn.close()

def update_balance(user_uuid, balance_change):
    """Updates the balance of a user by adding the balance_change value (positive or negative)."""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('BEGIN TRANSACTION')
        c.execute('UPDATE users SET balance = balance + ? WHERE uuid = ?', (balance_change, user_uuid))
        if c.rowcount == 0:
            logging.error(f"No rows updated. User {user_uuid} may not exist in the database.")
            conn.rollback()
            return None
        conn.commit()
        c.execute('SELECT balance FROM users WHERE uuid = ?', (user_uuid,))
        updated_balance = c.fetchone()
        return updated_balance[0] if updated_balance else None
    except sqlite3.Error as e:
        logging.error(f"Database error while updating balance for user {user_uuid}: {e}")
        if conn:
            conn.rollback()
        return None
    finally:
        conn.close()

def use_balance(user_uuid):
    """Attempts to use 1 balance unit for a user, returns True if successful."""
    try:
        balance = get_balance(user_uuid)
        if balance > 0:
            updated_balance = update_balance(user_uuid, -1)
            if updated_balance is not None:
                logging.info(f"Balance used successfully for user {user_uuid}. Remaining balance: {updated_balance}")
                return True
            else:
                logging.error(f"Failed to verify updated balance for user {user_uuid}.")
                return False
        else:
            logging.warning(f"Insufficient balance for user {user_uuid}.")
            return False
    except Exception as e:
        logging.error(f"Error in use_balance: {e}")
        return False

def get_user_agent(user_uuid):
    """Retrieves the stored user agent for a given user UUID."""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('SELECT user_agent FROM users WHERE uuid = ?', (user_uuid,))
        result = c.fetchone()
        return result[0] if result else None
    except sqlite3.Error as e:
        logging.error(f"Database error while retrieving user agent for user {user_uuid}: {e}")
        return None
    finally:
        conn.close()

def get_last_awarded(user_uuid):
    """Retrieves the last awarded timestamp for a given user UUID."""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('SELECT last_awarded FROM users WHERE uuid = ?', (user_uuid,))
        result = c.fetchone()
        return result[0] if result else 0
    except sqlite3.Error as e:
        logging.error(f"Database error while retrieving last awarded timestamp for user {user_uuid}: {e}")
        return 0
    finally:
        conn.close()

def update_last_awarded(user_uuid, last_awarded):
    """Updates the last awarded timestamp for a given user UUID."""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('UPDATE users SET last_awarded = ? WHERE uuid = ?', (last_awarded, user_uuid))
        conn.commit()
        logging.info(f"Last awarded timestamp for user {user_uuid} updated successfully.")
    except sqlite3.Error as e:
        logging.error(f"Database error while updating last awarded timestamp for user {user_uuid}: {e}")
    finally:
        conn.close()

def check_uuid_exists(user_uuid):
    """Checks if a given UUID exists in the database."""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('SELECT 1 FROM users WHERE uuid = ?', (user_uuid,))
        result = c.fetchone()
        return bool(result)
    except sqlite3.Error as e:
        logging.error(f"Database error while checking if user {user_uuid} exists: {e}")
        return False
    finally:
        conn.close()

def reset_all_balance():
    """Resets the balance of all users to zero (for development use)."""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('UPDATE users SET balance = 0')
        conn.commit()
        logging.info("All balances have been successfully reset to zero.")
    except sqlite3.Error as e:
        logging.error(f"Database error while resetting all balances: {e}")
    finally:
        conn.close()

def reset_all_users():
    """Deletes all users from the database (for development use)."""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('DELETE FROM users')
        conn.commit()
        logging.info("All users have been successfully removed from the database.")
    except sqlite3.Error as e:
        logging.error(f"Database error while resetting all users: {e}")
    finally:
        conn.close()
