import os
import sqlite3
import logging
import time
import uuid
import hashlib
from dotenv import load_dotenv

load_dotenv()

DB_FILE = 'uuid_balance.db'
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

logging.info(f"Using database file: {DB_FILE}")
logging.info(f"Running in Flask environment: {os.getenv('FLASK_ENV')}")

def init_db():
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
            logging.info("Database initialized successfully.")
    except sqlite3.Error as e:
        logging.error(f"Database initialization error: {e}")

def hash_user_agent(user_agent):
    """Hashes the user agent using SHA256."""
    return hashlib.sha256(user_agent.encode()).hexdigest()

def generate_uuid(user_agent, starting_balance=10):
    hashed_user_agent = hash_user_agent(user_agent)
    user_uuid = str(uuid.uuid4())
    add_user_record(user_uuid, hashed_user_agent, starting_balance)
    return user_uuid

def add_user_record(user_uuid, user_agent, starting_balance):
    if not user_uuid:
        logging.error("Cannot add user record: UUID is missing.")
        return
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute('INSERT INTO users (uuid, user_agent, balance, last_awarded) VALUES (?, ?, ?, ?)', 
                      (user_uuid, user_agent, starting_balance, int(time.time())))
            logging.info(f"User {user_uuid} added successfully. User-Agent='{user_agent}', Initial balance={starting_balance}.")
    except sqlite3.Error as e:
        logging.error(f"Database error while adding user {user_uuid}: {e}")

def get_balance(user_uuid):
    if not user_uuid:
        logging.error("Cannot retrieve balance: UUID is missing.")
        return 0
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute('SELECT balance FROM users WHERE uuid = ?', (user_uuid,))
            result = c.fetchone()
            return result[0] if result else 0
    except sqlite3.Error as e:
        logging.error(f"Database error while retrieving balance for user {user_uuid}: {e}")
        return 0

def update_balance(user_uuid, balance_change):
    if not user_uuid or balance_change == 0:
        logging.warning("Invalid parameters for updating balance.")
        return None
    try:
        with sqlite3.connect(DB_FILE) as conn:
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
            if updated_balance:
                logging.info(f"Balance for user {user_uuid} updated successfully. New balance: {updated_balance[0]}")
            return updated_balance[0] if updated_balance else None
    except sqlite3.Error as e:
        logging.error(f"Database error while updating balance for user {user_uuid}: {e}")
        return None

def use_balance(user_uuid):
    if not user_uuid:
        logging.error("Cannot use balance: UUID is missing.")
        return False
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

def get_user_agent(user_uuid):
    if not user_uuid:
        logging.error("Cannot retrieve user agent: UUID is missing.")
        return None
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute('SELECT user_agent FROM users WHERE uuid = ?', (user_uuid,))
            result = c.fetchone()
            if result:
                logging.info(f"User-Agent for user {user_uuid} retrieved successfully.")
            return result[0] if result else None
    except sqlite3.Error as e:
        logging.error(f"Database error while retrieving user agent for user {user_uuid}: {e}")
        return None

def update_user_agent(user_uuid, user_agent):
    hashed_user_agent = hash_user_agent(user_agent)
    if not user_uuid:
        logging.error("Cannot update user agent: UUID is missing.")
        return
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute('UPDATE users SET user_agent = ? WHERE uuid = ?', (hashed_user_agent, user_uuid))
            if c.rowcount > 0:
                logging.info(f"User agent for user {user_uuid} updated successfully. New hashed user-agent: '{hashed_user_agent}'")
            else:
                logging.warning(f"User agent update failed for user {user_uuid}. No matching record found.")
    except sqlite3.Error as e:
        logging.error(f"Database error while updating user agent for user {user_uuid}: {e}")

def get_last_awarded(user_uuid):
    if not user_uuid:
        logging.error("Cannot retrieve last awarded timestamp: UUID is missing.")
        return 0
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute('SELECT last_awarded FROM users WHERE uuid = ?', (user_uuid,))
            result = c.fetchone()
            if result:
                logging.info(f"Last awarded timestamp for user {user_uuid} retrieved successfully.")
            return result[0] if result else 0
    except sqlite3.Error as e:
        logging.error(f"Database error while retrieving last awarded timestamp for user {user_uuid}: {e}")
        return 0

def update_last_awarded(user_uuid, last_awarded):
    if not user_uuid:
        logging.error("Cannot update last awarded: UUID is missing.")
        return
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute('UPDATE users SET last_awarded = ? WHERE uuid = ?', (last_awarded, user_uuid))
            if c.rowcount > 0:
                logging.info(f"Last awarded timestamp for user {user_uuid} updated successfully.")
            else:
                logging.warning(f"Last awarded timestamp update failed for user {user_uuid}. No matching record found.")
    except sqlite3.Error as e:
        logging.error(f"Database error while updating last awarded timestamp for user {user_uuid}: {e}")

def check_uuid_exists(user_uuid):
    if not user_uuid:
        logging.error("Cannot check UUID existence: UUID is missing.")
        return False
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute('SELECT 1 FROM users WHERE uuid = ?', (user_uuid,))
            result = c.fetchone()
            if result:
                logging.info(f"UUID {user_uuid} exists in the database.")
            else:
                logging.warning(f"UUID {user_uuid} does not exist in the database.")
            return bool(result)
    except sqlite3.Error as e:
        logging.error(f"Database error while checking if user {user_uuid} exists: {e}")
        return False

def clear_all_balances():
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute('UPDATE users SET balance = 0')
            logging.info("All balances have been successfully cleared to zero.")
    except sqlite3.Error as e:
        logging.error(f"Database error while clearing all balances: {e}")

def delete_user_record(user_uuid):
    if not user_uuid:
        logging.error("Cannot delete user record: UUID is missing.")
        return
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute('DELETE FROM users WHERE uuid = ?', (user_uuid,))
            if c.rowcount > 0:
                logging.info(f"User record for UUID {user_uuid} has been successfully deleted.")
            else:
                logging.warning(f"User record for UUID {user_uuid} does not exist.")
    except sqlite3.Error as e:
        logging.error(f"Database error while deleting user record {user_uuid}: {e}")

def delete_all_user_records():
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute('DELETE FROM users')
            logging.info("All user records have been successfully deleted from the database.")
    except sqlite3.Error as e:
        logging.error(f"Database error while deleting all user records: {e}")
