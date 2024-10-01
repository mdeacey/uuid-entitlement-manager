import os
import uuid
import time
import logging
from dotenv import load_dotenv
import database

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Helper function to parse environment variable lists
def parse_env_list(env_var, separator=",", key_value_separator=":"):
    """Parses an environment variable into a dictionary."""
    items = os.getenv(env_var, "")
    result = {}
    if items:
        for item in items.split(separator):
            key, value = item.split(key_value_separator)
            result[key.strip()] = int(value.strip())
    return result

# Parse balance packs and coupons from the environment
BALANCE_PACKS = parse_env_list('BALANCE_PACKS')
logging.info(f"BALANCE_PACKS: {BALANCE_PACKS}")

COUPONS = parse_env_list('COUPONS')
logging.info(f"COUPONS: {COUPONS}")

def get_balance_type():
    """Retrieve the customizable term for balance (e.g., Balance, Credits, Tokens)."""
    return os.getenv('BALANCE_TYPE', 'Balance')

def generate_uuid(user_agent, starting_balance=10):
    """Generates a UUID for a new user and adds them to the database."""
    user_uuid = str(uuid.uuid4())
    database.add_user(user_uuid, user_agent, starting_balance)
    logging.info(f"Generated UUID for user: {user_uuid}")
    return user_uuid

def get_balance(user_uuid):
    """Retrieves the current balance for a user, applying free balance if eligible."""
    try:
        last_awarded = database.get_last_awarded(user_uuid)
        current_time = int(time.time())
        free_balance_interval = int(os.getenv('FREE_BALANCE_INTERVAL', 86400))
        free_balance_amount = int(os.getenv('FREE_BALANCE', 10))

        # Award free balance if enough time has passed since the last award
        if current_time - last_awarded >= free_balance_interval:
            logging.info(f"Awarding {free_balance_amount} {get_balance_type()} to user {user_uuid}.")
            database.update_balance(user_uuid, free_balance_amount)
            database.update_last_awarded(user_uuid, current_time)

        return database.get_balance(user_uuid)
    except Exception as e:
        logging.error(f"Error in get_balance: {e}")
        return 0

def update_balance(user_uuid, balance):
    """Updates the balance for a user."""
    updated_balance = database.update_balance(user_uuid, balance)
    if updated_balance is not None:
        logging.info(f"Updated {get_balance_type()} for user {user_uuid}: {updated_balance}")
    else:
        logging.error(f"Failed to update {get_balance_type()} for user {user_uuid}.")

def process_payment(user_uuid, balance_pack, discount):
    """Processes payment for the given balance pack, applying any discount."""
    try:
        if balance_pack not in BALANCE_PACKS:
            raise ValueError("Invalid balance pack selected.")

        balance_amount = BALANCE_PACKS[balance_pack]

        # Apply discount if any
        final_amount = max(0, balance_amount - discount)

        # Redirect URL for payment gateway
        payment_url = os.getenv('PAYMENT_URL').format(user_uuid=user_uuid, balance=final_amount)
        logging.info(f"Redirecting user {user_uuid} to payment URL: {payment_url}")
        return payment_url
    except Exception as e:
        logging.error(f"Error in process_payment: {e}")
        raise

def validate_coupon(coupon_code):
    """Validates a coupon code and returns its discount value."""
    discount = COUPONS.get(coupon_code)
    is_valid = coupon_code in COUPONS
    if is_valid:
        logging.info(f"Coupon code {coupon_code} is valid with a discount of {discount}.")
    else:
        logging.warning(f"Coupon code {coupon_code} is invalid.")
    return is_valid, discount if discount else 0

def use_balance(user_uuid):
    """Uses 1 unit of balance from a user's account, if available."""
    try:
        balance = database.get_balance(user_uuid)
        if balance > 0:
            updated_balance = database.update_balance(user_uuid, -1)
            if updated_balance is not None:
                logging.info(f"{get_balance_type()} used successfully for user {user_uuid}. Remaining {get_balance_type()}: {updated_balance}")
                return True
            else:
                logging.error(f"Failed to verify updated {get_balance_type()} for user {user_uuid}.")
                return False
        else:
            logging.warning(f"Insufficient {get_balance_type()} for user {user_uuid}.")
            return False
    except Exception as e:
        logging.error(f"Error in use_balance: {e}")
        return False

def add_balance_manually(user_uuid, balance_to_add):
    """Manually adds a specified balance to a user's account (used for development or testing)."""
    try:
        updated_balance = database.update_balance(user_uuid, balance_to_add)
        if updated_balance is not None:
            logging.info(f"Manually added {balance_to_add} {get_balance_type()} to user {user_uuid}. New {get_balance_type()}: {updated_balance}")
        else:
            logging.error(f"Failed to add {get_balance_type()} to user {user_uuid}.")
    except Exception as e:
        logging.error(f"Error in add_balance_manually: {e}")
