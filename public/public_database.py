import sqlite3
import time
import uuid
import hashlib
from shared.shared_database import get_database_connection
from shared.utils.logging import logger

def hash_user_agent(user_agent):
    hashed_agent = hashlib.sha256(user_agent.encode()).hexdigest()
    logger.debug("Hashed user agent for logging.")
    return hashed_agent

def generate_uuid(user_agent, starting_balance=10):
    hashed_user_agent = hash_user_agent(user_agent)
    user_uuid = str(uuid.uuid4())
    logger.info("Generating UUID for new user with initial balance '{}'...", starting_balance)
    add_user_record(user_uuid, hashed_user_agent, starting_balance)
    return user_uuid

def add_user_record(user_uuid, user_agent, starting_balance):
    try:
        with get_database_connection() as conn:
            c = conn.cursor()
            c.execute(
                'INSERT INTO users (uuid, user_agent, balance, last_awarded) VALUES (?, ?, ?, ?)',
                (user_uuid, user_agent, starting_balance, int(time.time()))
            )
            logger.info("User record added: UUID='{}', Initial balance='{}'.", user_uuid, starting_balance)
    except sqlite3.Error as e:
        logger.exception("Public database error while adding user record for UUID '{}': {}", user_uuid, e)

def get_balance(user_uuid):
    try:
        with get_database_connection() as conn:
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
        logger.exception("Public database error while retrieving balance for UUID '{}': {}", user_uuid, e)
        return 0

def update_balance(user_uuid, balance_change):
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
        logger.exception("Public database error while updating balance for UUID '{}': {}", user_uuid, e)
        return None

def use_balance(user_uuid):
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
        logger.exception("Public database error while retrieving user agent for UUID '{}': {}", user_uuid, e)
        return None

def update_user_agent(user_uuid, user_agent):
    hashed_user_agent = hash_user_agent(user_agent)
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute('UPDATE users SET user_agent = ? WHERE uuid = ?', (hashed_user_agent, user_uuid))
            if c.rowcount > 0:
                logger.info("User agent updated for user '{}'.", user_uuid)
            else:
                logger.warning("User agent update failed for user '{}'. No matching record found.", user_uuid)
    except sqlite3.Error as e:
        logger.exception("Public database error while updating user agent for UUID '{}': {}", user_uuid, e)

def check_uuid_exists(user_uuid):
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
        logger.exception("Public database error while checking if UUID '{}' exists: {}", user_uuid, e)
        return False

def add_purchase_pack(pack_name, original_name, size, price, currency):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute('''
                INSERT OR REPLACE INTO purchase_packs (pack_name, original_name, size, price, currency)
                VALUES (?, ?, ?, ?, ?)
            ''', (pack_name, original_name, size, price, currency))
            logger.info("Purchase pack '{}' added/updated successfully.", original_name)
    except sqlite3.Error as e:
        logger.exception("Public database error while adding/updating purchase pack '{}': {}", original_name, e)

def get_purchase_packs():
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
            logger.info("Retrieved purchase packs from public database.")
            return packs
    except sqlite3.Error as e:
        logger.exception("Public database error while retrieving purchase packs: {}", e)
        return {}

def add_coupon(coupon_code, discount, applicable_packs):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute('''
                INSERT OR REPLACE INTO coupons (coupon_code, discount, applicable_packs)
                VALUES (?, ?, ?)
            ''', (coupon_code, discount, applicable_packs))
            logger.info("Coupon '{}' added/updated successfully.", coupon_code)
    except sqlite3.Error as e:
        logger.exception("Public database error while adding/updating coupon '{}': {}", coupon_code, e)

def get_coupons():
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
            logger.info("Retrieved coupons from public database.")
            return coupons
    except sqlite3.Error as e:
        logger.exception("Public database error while retrieving coupons: {}", e)
        return {}
