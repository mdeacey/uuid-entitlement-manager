import os
import sqlite3
import time
import uuid
import hashlib
from dotenv import load_dotenv
from utils.logging import logger

# Load environment variables
load_dotenv()

# Database file path from environment
DB_FILE = os.getenv('DATABASE_FILE', 'uuid_balance.db')

def init_db():
    """
    Initialize the SQLite database.
    Creates the 'users', 'purchase_packs', and 'coupons' tables if they do not exist.
    """
    # Log which database file is being used and environment information
    logger.info("Initializing database:'{}'...", DB_FILE)
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
            c.execute('''
                CREATE TABLE IF NOT EXISTS coupons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    coupon_code TEXT UNIQUE,
                    discount INTEGER,
                    applicable_packs TEXT
                )
            ''')
    except sqlite3.Error as e:
        logger.exception("Database initialization error: {}", e)

def get_db_file():
    """
    Get the path to the database file being used.
    """
    return DB_FILE

def hash_user_agent(user_agent):
    """
    Hashes the user agent using SHA256.
    """
    hashed_agent = hashlib.sha256(user_agent.encode()).hexdigest()
    logger.debug("Hashed user agent for logging.")
    return hashed_agent

def generate_uuid(user_agent, starting_balance=10):
    """
    Generates a UUID for a new user and adds a new record to the database.
    """
    hashed_user_agent = hash_user_agent(user_agent)
    user_uuid = str(uuid.uuid4())
    logger.info("Generating UUID for new user with initial balance '{}'...", starting_balance)
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
            c.execute(
                'INSERT INTO users (uuid, user_agent, balance, last_awarded) VALUES (?, ?, ?, ?)',
                (user_uuid, user_agent, starting_balance, int(time.time()))
            )
            logger.info("User record added: UUID='{}', Initial balance='{}'.", user_uuid, starting_balance)
    except sqlite3.Error as e:
        logger.exception("Database error while adding user record for UUID '{}': {}", user_uuid, e)

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
                logger.info("Retrieved balance for user '{}': {}", user_uuid, result[0])
                return result[0]
            else:
                logger.warning("No record found for UUID '{}'. Returning balance as 0.", user_uuid)
                return 0
    except sqlite3.Error as e:
        logger.exception("Database error while retrieving balance for UUID '{}': {}", user_uuid, e)
        return 0

def update_balance(user_uuid, balance_change):
    """
    Updates the balance of a user.
    """
    if not user_uuid or balance_change == 0:
        logger.warning("Invalid parameters for updating balance: UUID='{}', Balance change='{}'.", user_uuid, balance_change)
        return None
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute('BEGIN TRANSACTION')
            c.execute('UPDATE users SET balance = balance + ? WHERE uuid = ?', (balance_change, user_uuid))
            if c.rowcount == 0:
                logger.error("No record found to update balance for UUID '{}'. Rolling back.", user_uuid)
                conn.rollback()
                return None
            conn.commit()
            c.execute('SELECT balance FROM users WHERE uuid = ?', (user_uuid,))
            updated_balance = c.fetchone()
            if updated_balance:
                logger.info("Balance updated for user '{}'. New balance: {}", user_uuid, updated_balance[0])
                return updated_balance[0]
            else:
                logger.error("Failed to retrieve updated balance for UUID '{}' after update.", user_uuid)
                return None
    except sqlite3.Error as e:
        logger.exception("Database error while updating balance for UUID '{}': {}", user_uuid, e)
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
            logger.info("Balance used for user '{}'. Remaining balance: {}", user_uuid, updated_balance)
            return True
        else:
            logger.error("Failed to verify updated balance for UUID '{}' after usage.", user_uuid)
            return False
    else:
        logger.warning("Insufficient balance for user '{}'. Balance is '{}'.", user_uuid, balance)
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
                logger.info("Retrieved user agent for user '{}'.", user_uuid)
                return result[0]
            else:
                logger.warning("No record found for UUID '{}' to retrieve user agent.", user_uuid)
                return None
    except sqlite3.Error as e:
        logger.exception("Database error while retrieving user agent for UUID '{}': {}", user_uuid, e)
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
                logger.info("User agent updated for user '{}'.", user_uuid)
            else:
                logger.warning("User agent update failed for user '{}'. No matching record found.", user_uuid)
    except sqlite3.Error as e:
        logger.exception("Database error while updating user agent for UUID '{}': {}", user_uuid, e)

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
                logger.info("Retrieved last awarded timestamp for user '{}'.", user_uuid)
                return result[0]
            else:
                logger.warning("No record found for UUID '{}' to retrieve last awarded timestamp.", user_uuid)
                return 0
    except sqlite3.Error as e:
        logger.exception("Database error while retrieving last awarded timestamp for UUID '{}': {}", user_uuid, e)
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
                logger.info("Last awarded timestamp updated for user '{}'.", user_uuid)
            else:
                logger.warning("Last awarded timestamp update failed for UUID '{}'. No matching record found.", user_uuid)
    except sqlite3.Error as e:
        logger.exception("Database error while updating last awarded timestamp for UUID '{}': {}", user_uuid, e)

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
                logger.info("UUID '{}' exists in the database.", user_uuid)
                return True
            else:
                logger.warning("UUID '{}' does not exist in the database.", user_uuid)
                return False
    except sqlite3.Error as e:
        logger.exception("Database error while checking if UUID '{}' exists: {}", user_uuid, e)
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
        logger.exception("Database error while clearing all balances: {}", e)

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
                logger.info("User record for UUID '{}' has been successfully deleted.", user_uuid)
            else:
                logger.warning("User record for UUID '{}' does not exist.", user_uuid)
    except sqlite3.Error as e:
        logger.exception("Database error while deleting user record for UUID '{}': {}", user_uuid, e)

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
        logger.exception("Database error while deleting all user records: {}", e)

def add_purchase_pack(pack_name, original_name, size, price, currency):
    """
    Adds or updates a purchase pack in the database.
    """
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute('''
                INSERT OR REPLACE INTO purchase_packs (pack_name, original_name, size, price, currency)
                VALUES (?, ?, ?, ?, ?)
            ''', (pack_name, original_name, size, price, currency))
            logger.info("Purchase pack '{}' added/updated successfully.", original_name)
    except sqlite3.Error as e:
        logger.exception("Database error while adding/updating purchase pack '{}': {}", original_name, e)

def get_purchase_packs():
    """
    Retrieves all purchase packs from the database.
    """
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute('SELECT pack_name, original_name, size, price, currency FROM purchase_packs')
            rows = c.fetchall()
            packs = {}
            for row in rows:
                pack_name, original_name, size, price, currency = row
                packs[pack_name] = {
                    "original_name": original_name,
                    "size": size,
                    "price": price,
                    "currency": currency
                }
            logger.info("Retrieved purchase packs from database.")
            return packs
    except sqlite3.Error as e:
        logger.exception("Database error while retrieving purchase packs: {}", e)
        return {}

def add_coupon(coupon_code, discount, applicable_packs):
    """
    Adds or updates a coupon in the database.
    """
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute('''
                INSERT OR REPLACE INTO coupons (coupon_code, discount, applicable_packs)
                VALUES (?, ?, ?)
            ''', (coupon_code, discount, applicable_packs))
            logger.info("Coupon '{}' added/updated successfully.", coupon_code)
    except sqlite3.Error as e:
        logger.exception("Database error while adding/updating coupon '{}': {}", coupon_code, e)

def get_coupons():
    """
    Retrieves all coupons from the database.
    """
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute('SELECT coupon_code, discount, applicable_packs FROM coupons')
            rows = c.fetchall()
            coupons = {}
            for row in rows:
                coupon_code, discount, applicable_packs = row
                coupons[coupon_code] = {
                    "discount": discount,
                    "applicable_packs": applicable_packs.split(",")
                }
            logger.info("Retrieved coupons from database.")
            return coupons
    except sqlite3.Error as e:
        logger.exception("Database error while retrieving coupons: {}", e)
        return {}
