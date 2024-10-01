import sqlite3
import logging
from config import Config

DB_FILE = Config.DATABASE_FILE

def init_db():
    try:
        conn = sqlite3.connect(Config.DATABASE_FILE)
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
        conn = sqlite3.connect(Config.DATABASE_FILE)
        c = conn.cursor()
        c.execute('INSERT INTO users (uuid, user_agent, credits, last_awarded) VALUES (?, ?, ?, ?)', 
                  (user_uuid, user_agent, starting_credits, int(time.time())))
        conn.commit()

        # Verify that the user was inserted
        c.execute('SELECT * FROM users WHERE uuid = ?', (user_uuid,))
        user = c.fetchone()
        if user:
            logging.info(f"User {user_uuid} verified in database after insert.")
        else:
            logging.error(f"User {user_uuid} not found in database after insert.")
    except sqlite3.Error as e:
        logging.error(f"Database error while adding user: {e}")
    finally:
        conn.close()



def get_credits(user_uuid):
    try:
        logging.info(f"Retrieving credits for user {user_uuid}")
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('SELECT credits FROM users WHERE uuid = ?', (user_uuid,))
        result = c.fetchone()
        if result:
            logging.info(f"User {user_uuid} has {result[0]} credits.")
        return result[0] if result else 0
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
        return 0
    finally:
        conn.close()

def update_credits(user_uuid, credits):
    try:
        logging.info(f"Attempting to update credits for user {user_uuid} by {credits}.")
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('BEGIN TRANSACTION')
        c.execute('UPDATE users SET credits = credits + ? WHERE uuid = ?', (credits, user_uuid))
        if c.rowcount == 0:
            logging.error(f"No rows updated. User {user_uuid} may not exist in the database.")
            c.execute('SELECT * FROM users')
            users = c.fetchall()
            logging.info(f"Current users in database: {users}")
            conn.rollback()
            return None
        conn.commit()
        logging.info(f"Credits for user {user_uuid} updated successfully by {credits}.")
        c.execute('SELECT credits FROM users WHERE uuid = ?', (user_uuid,))
        updated_credits = c.fetchone()
        if updated_credits:
            logging.info(f"User {user_uuid} now has {updated_credits[0]} credits.")
            return updated_credits[0]
        else:
            logging.error(f"Failed to retrieve updated credits for user {user_uuid} after update.")
            return None
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
        if conn:
            conn.rollback()
        return None
    finally:
        if conn:
            conn.close()

def get_last_awarded(user_uuid):
    try:
        logging.info(f"Retrieving last awarded timestamp for user {user_uuid}")
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('SELECT last_awarded FROM users WHERE uuid = ?', (user_uuid,))
        result = c.fetchone()
        if result:
            logging.info(f"User {user_uuid} last awarded at {result[0]}")
        return result[0] if result else 0
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
        return 0
    finally:
        conn.close()

def update_last_awarded(user_uuid, last_awarded):
    try:
        logging.info(f"Updating last awarded timestamp for user {user_uuid} to {last_awarded}")
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('UPDATE users SET last_awarded = ? WHERE uuid = ?', (last_awarded, user_uuid))
        conn.commit()
        logging.info(f"Last awarded timestamp for user {user_uuid} updated successfully.")
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
    finally:
        conn.close()

def check_uuid_exists(user_uuid):
    try:
        logging.info(f"Checking if user {user_uuid} exists in database.")
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('SELECT 1 FROM users WHERE uuid = ?', (user_uuid,))
        result = c.fetchone()
        if result:
            logging.info(f"User {user_uuid} exists in database.")
        else:
            logging.info(f"User {user_uuid} does not exist in database.")
        return bool(result)
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
        return False
    finally:
        conn.close()

def get_user_agent(user_uuid):
    try:
        logging.info(f"Retrieving user agent for user {user_uuid}")
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('SELECT user_agent FROM users WHERE uuid = ?', (user_uuid,))
        result = c.fetchone()
        if result:
            logging.info(f"User {user_uuid} has user agent {result[0]}")
        return result[0] if result else None
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
        return None
    finally:
        conn.close()

def reset_all_credits():
    try:
        logging.info("Resetting all user credits to zero.")
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('UPDATE users SET credits = 0')
        conn.commit()
        c.execute('SELECT COUNT(*) FROM users WHERE credits > 0')
        remaining_credits = c.fetchone()[0]
        if remaining_credits == 0:
            logging.info("All credits have been successfully reset to zero.")
        else:
            logging.error(f"Some users still have credits remaining after reset. Users with credits: {remaining_credits}")
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
    finally:
        conn.close()
