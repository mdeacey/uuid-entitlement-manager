import sqlite3
import logging
from config import Config
import time

DB_FILE = Config.DATABASE_FILE

def init_db():
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                uuid TEXT PRIMARY KEY, 
                user_agent TEXT,
                credits INTEGER,
                last_awarded INTEGER
            )
        ''')
        conn.commit()
        logging.info("Database initialized successfully.")
    except sqlite3.Error as e:
        logging.error(f"Database initialization error: {e}")
    finally:
        conn.close()


def add_user(user_uuid, user_agent, starting_credits):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('INSERT INTO users (uuid, user_agent, credits, last_awarded) VALUES (?, ?, ?, ?)', 
                  (user_uuid, user_agent, starting_credits, int(time.time())))
        conn.commit()
        logging.info(f"User {user_uuid} added successfully.")
    except sqlite3.Error as e:
        logging.error(f"Database error while adding user: {e}")
    finally:
        conn.close()


def get_credits(user_uuid):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('SELECT credits FROM users WHERE uuid = ?', (user_uuid,))
        result = c.fetchone()
        return result[0] if result else 0
    except sqlite3.Error as e:
        logging.error(f"Database error while retrieving credits for user {user_uuid}: {e}")
        return 0
    finally:
        conn.close()


def update_credits(user_uuid, credits):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('BEGIN TRANSACTION')
        c.execute('UPDATE users SET credits = credits + ? WHERE uuid = ?', (credits, user_uuid))
        if c.rowcount == 0:
            logging.error(f"No rows updated. User {user_uuid} may not exist in the database.")
            conn.rollback()
            return None
        conn.commit()
        c.execute('SELECT credits FROM users WHERE uuid = ?', (user_uuid,))
        updated_credits = c.fetchone()
        return updated_credits[0] if updated_credits else None
    except sqlite3.Error as e:
        logging.error(f"Database error while updating credits for user {user_uuid}: {e}")
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


def reset_all_credits():
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('UPDATE users SET credits = 0')
        conn.commit()
        logging.info("All credits have been successfully reset to zero.")
    except sqlite3.Error as e:
        logging.error(f"Database error while resetting all credits: {e}")
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
