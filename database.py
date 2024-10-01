import sqlite3
import logging
from config import Config
import time

DB_FILE = Config.DATABASE_FILE
logging.info(f"Using database file: {DB_FILE}")
logging.info(f"Running in Flask environment: {Config.FLASK_ENV}")

def init_db():
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

def add_user(user_uuid, user_agent, starting_balance):
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

def update_balance(user_uuid, balance):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('BEGIN TRANSACTION')
        c.execute('UPDATE users SET balance = balance + ? WHERE uuid = ?', (balance, user_uuid))
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

def get_last_awarded(user_uuid):
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

def get_user_agent(user_uuid):
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

def reset_all_balance():
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('UPDATE users SET balance = 0')
        conn.commit()
        logging.info("All balance has been successfully reset to zero.")
    except sqlite3.Error as e:
        logging.error(f"Database error while resetting all balance: {e}")
    finally:
        conn.close()

def reset_all_users():
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
