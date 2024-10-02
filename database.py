import os
import sqlite3
import logging
import time
import uuid
import hashlib
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database file path
DB_FILE = os.getenv('DATABASE_FILE', 'uuid_balance.db')

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('uuid_entitlement_manager.database')

# Log which database file is being used and environment information
logger.info(f"Using database file: {DB_FILE}")
logger.info(f"Running in Flask environment: {os.getenv('FLASK_ENV')}")

def init_db():
    """
    Initialize the SQLite database.
    Creates the 'users' table if it does not exist.
    """
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
            logger.info("Database initialized successfully.")
    except sqlite3.Error as e:
        logger.error(f"Database initialization error: {e}")

def hash_user_agent(user_agent):
    """
    Hashes the user agent using SHA256.
    """
    return hashlib.sha256(user_agent.encode()).hexdigest()

def generate_uuid(user_agent, starting_balance=10):
    """
    Generates a UUID for a new user and adds a new record to the database.
    """
    hashed_user_agent = hash_user_agent(user_agent)
    user_uuid = str(uuid.uuid4())
    add_user_record(user_uuid, hashed_user_agent, starting_balance)
    return user_uuid

def add_user_record(user_uuid, user_agent, starting_balance):
    """
    Adds a new user record to the database.
    """
    if not user_uuid:
        logger.error("Cannot add user record: UUID is missing.")
        return
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute('INSERT INTO users (uuid, user_agent, balance, last_awarded) VALUES (?, ?, ?, ?)', 
                      (user_uuid, user_agent, starting_balance, int(time.time())))
            logger.info(f"User record added: UUID={user_uuid}, Initial balance={starting_balance}.")
    except sqlite3.Error as e:
        logger.error(f"Database error while adding user record for UUID {user_uuid}: {e}")

def get_balance(user_uuid):
    """
    Retrieves the balance of a user by their UUID.
    """
    if not user_uuid:
        logger.error("Cannot retrieve balance: UUID is missing.")
        return 0
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute('SELECT balance FROM users WHERE uuid = ?', (user_uuid,))
            result = c.fetchone()
            if result:
                logger.info(f"Retrieved balance for user {user_uuid}: {result[0]}")
                return result[0]
            else:
                logger.warning(f"No record found for UUID {user_uuid}. Returning balance as 0.")
                return 0
    except sqlite3.Error as e:
        logger.error(f"Database error while retrieving balance for UUID {user_uuid}: {e}")
        return 0

def update_balance(user_uuid, balance_change):
    """
    Updates the balance of a user.
    """
    if not user_uuid or balance_change == 0:
        logger.warning(f"Invalid parameters for updating balance: UUID={user_uuid}, Balance change={balance_change}.")
        return None
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute('BEGIN TRANSACTION')
            c.execute('UPDATE users SET balance = balance + ? WHERE uuid = ?', (balance_change, user_uuid))
            if c.rowcount == 0:
                logger.error(f"No record found to update balance for UUID {user_uuid}.")
                conn.rollback()
                return None
            conn.commit()
            c.execute('SELECT balance FROM users WHERE uuid = ?', (user_uuid,))
            updated_balance = c.fetchone()
            if updated_balance:
                logger.info(f"Balance updated for user {user_uuid}. New balance: {updated_balance[0]}")
                return updated_balance[0]
            else:
                logger.error(f"Failed to retrieve updated balance for UUID {user_uuid} after update.")
                return None
    except sqlite3.Error as e:
        logger.error(f"Database error while updating balance for UUID {user_uuid}: {e}")
        return None

def use_balance(user_uuid):
    """
    Decreases the balance of a user by 1 if they have enough balance.
    """
    if not user_uuid:
        logger.error("Cannot use balance: UUID is missing.")
        return False
    balance = get_balance(user_uuid)
    if balance > 0:
        updated_balance = update_balance(user_uuid, -1)
        if updated_balance is not None:
            logger.info(f"Balance used for user {user_uuid}. Remaining balance: {updated_balance}")
            return True
        else:
            logger.error(f"Failed to verify updated balance for UUID {user_uuid} after usage.")
            return False
    else:
        logger.warning(f"Insufficient balance for user {user_uuid}. Balance is {balance}.")
        return False

def get_user_agent(user_uuid):
    """
    Retrieves the hashed user agent associated with a user by their UUID.
    """
    if not user_uuid:
        logger.error("Cannot retrieve user agent: UUID is missing.")
        return None
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute('SELECT user_agent FROM users WHERE uuid = ?', (user_uuid,))
            result = c.fetchone()
            if result:
                logger.info(f"Retrieved user agent for user {user_uuid}.")
                return result[0]
            else:
                logger.warning(f"No record found for UUID {user_uuid} to retrieve user agent.")
                return None
    except sqlite3.Error as e:
        logger.error(f"Database error while retrieving user agent for UUID {user_uuid}: {e}")
        return None

def update_user_agent(user_uuid, user_agent):
    """
    Updates the user agent for a given user UUID.
    """
    hashed_user_agent = hash_user_agent(user_agent)
    if not user_uuid:
        logger.error("Cannot update user agent: UUID is missing.")
        return
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute('UPDATE users SET user_agent = ? WHERE uuid = ?', (hashed_user_agent, user_uuid))
            if c.rowcount > 0:
                logger.info(f"User agent updated for user {user_uuid}.")
            else:
                logger.warning(f"User agent update failed for user {user_uuid}. No matching record found.")
    except sqlite3.Error as e:
        logger.error(f"Database error while updating user agent for UUID {user_uuid}: {e}")

def get_last_awarded(user_uuid):
    """
    Retrieves the last awarded timestamp for a user by their UUID.
    """
    if not user_uuid:
        logger.error("Cannot retrieve last awarded timestamp: UUID is missing.")
        return 0
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute('SELECT last_awarded FROM users WHERE uuid = ?', (user_uuid,))
            result = c.fetchone()
            if result:
                logger.info(f"Retrieved last awarded timestamp for user {user_uuid}.")
                return result[0]
            else:
                logger.warning(f"No record found for UUID {user_uuid} to retrieve last awarded timestamp.")
                return 0
    except sqlite3.Error as e:
        logger.error(f"Database error while retrieving last awarded timestamp for UUID {user_uuid}: {e}")
        return 0

def update_last_awarded(user_uuid, last_awarded):
    """
    Updates the last awarded timestamp for a given user UUID.
    """
    if not user_uuid:
        logger.error("Cannot update last awarded: UUID is missing.")
        return
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute('UPDATE users SET last_awarded = ? WHERE uuid = ?', (last_awarded, user_uuid))
            if c.rowcount > 0:
                logger.info(f"Last awarded timestamp updated for user {user_uuid}.")
            else:
                logger.warning(f"Last awarded timestamp update failed for UUID {user_uuid}. No matching record found.")
    except sqlite3.Error as e:
        logger.error(f"Database error while updating last awarded timestamp for UUID {user_uuid}: {e}")

def check_uuid_exists(user_uuid):
    """
    Checks whether a user UUID exists in the database.
    """
    if not user_uuid:
        logger.error("Cannot check UUID existence: UUID is missing.")
        return False
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute('SELECT 1 FROM users WHERE uuid = ?', (user_uuid,))
            result = c.fetchone()
            if result:
                logger.info(f"UUID {user_uuid} exists in the database.")
                return True
            else:
                logger.warning(f"UUID {user_uuid} does not exist in the database.")
                return False
    except sqlite3.Error as e:
        logger.error(f"Database error while checking if UUID {user_uuid} exists: {e}")
        return False

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
        logger.error(f"Database error while clearing all balances: {e}")

def delete_user_record(user_uuid):
    """
    Deletes a user record from the database by their UUID.
    """
    if not user_uuid:
        logger.error("Cannot delete user record: UUID is missing.")
        return
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute('DELETE FROM users WHERE uuid = ?', (user_uuid,))
            if c.rowcount > 0:
                logger.info(f"User record for UUID {user_uuid} has been successfully deleted.")
            else:
                logger.warning(f"User record for UUID {user_uuid} does not exist.")
    except sqlite3.Error as e:
        logger.error(f"Database error while deleting user record for UUID {user_uuid}: {e}")

def delete_all_user_records():
    """
    Deletes all user records from the database.
    """
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute('DELETE FROM users')
            logger.info("All user records have been successfully deleted from the database.")
    except sqlite3.Error as e:
        logger.error(f"Database error while deleting all user records: {e}")
