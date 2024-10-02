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

def parse_env_list(env_var, separator=";", key_value_separator=":"):
    """Parses an environment variable into a dictionary with coupons and their applicable packs."""
    items = os.getenv(env_var, "")
    result = {}
    if items:
        for item in items.split(separator):
            parts = item.split(key_value_separator)
            if len(parts) == 3:
                code, discount, packs = parts
                result[code.strip()] = {
                    "discount": int(discount.strip()),
                    "packs": [pack.strip() for pack in packs.split(",")]
                }
    return result

# Parse balance packs and coupons from the environment once and store them
BALANCE_PACKS = parse_env_list('BALANCE_PACKS')
logging.info(f"BALANCE_PACKS parsed from environment: {BALANCE_PACKS}")

COUPONS = parse_env_list('COUPONS')
logging.info(f"COUPONS parsed from environment: {COUPONS}")

def get_balance_type():
    """Retrieve the customizable term for balance (e.g., Balance, Credits, Tokens)."""
    balance_type = os.getenv('BALANCE_TYPE', 'Balance')
    logging.info(f"Retrieved balance type: {balance_type}")
    return balance_type

def format_currency(amount):
    """Formats the given amount based on the currency unit and decimal settings."""
    currency_unit = os.getenv('CURRENCY_UNIT', '$')
    decimals = int(os.getenv('CURRENCY_DECIMALS', 2))

    formatted_amount = f"{currency_unit}{amount:.{decimals}f}"
    logging.info(f"Formatted currency: {formatted_amount}")
    return formatted_amount

def generate_uuid(user_agent, starting_balance=10):
    """Generates a UUID for a new user and adds them to the database."""
    hashed_user_agent = database.hash_user_agent(user_agent)
    user_uuid = str(uuid.uuid4())
    database.add_user_record(user_uuid, hashed_user_agent, starting_balance)
    logging.info(f"Generated UUID for new user: {user_uuid}")
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
            logging.info(f"Free balance of {free_balance_amount} being awarded to user {user_uuid}.")
            database.update_balance(user_uuid, free_balance_amount)
            database.update_last_awarded(user_uuid, current_time)

        balance = database.get_balance(user_uuid)
        logging.info(f"Retrieved balance for user {user_uuid}: {balance}")
        return balance
    except Exception as e:
        logging.error(f"Error in get_balance for user {user_uuid}: {e}")
        return 0

def update_balance(user_uuid, balance_change):
    """Updates the balance for a user."""
    updated_balance = database.update_balance(user_uuid, balance_change)
    if updated_balance is not None:
        logging.info(f"Updated balance for user {user_uuid}: New balance is {updated_balance}.")
    else:
        logging.error(f"Failed to update balance for user {user_uuid}.")

def process_payment(user_uuid, balance_pack, discount):
    """Processes payment for the given balance pack, applying any discount."""
    try:
        if balance_pack not in BALANCE_PACKS:
            raise ValueError("Invalid balance pack selected.")

        balance_amount = BALANCE_PACKS[balance_pack]["amount"]

        # Apply discount if any
        final_amount = max(0, balance_amount - (balance_amount * discount / 100))

        # Format the amount for display
        formatted_amount = format_currency(final_amount)

        # Redirect URL for payment gateway
        payment_url = os.getenv('PAYMENT_URL').format(user_uuid=user_uuid, balance=formatted_amount)
        logging.info(f"Redirecting user {user_uuid} to payment URL: {payment_url} for {formatted_amount}")
        return payment_url
    except Exception as e:
        logging.error(f"Error in process_payment for user {user_uuid}: {e}")
        raise

def validate_coupon(coupon_code, balance_pack):
    """Validates a coupon code and checks if it is applicable to the selected balance pack."""
    coupon_data = COUPONS.get(coupon_code)
    if coupon_data:
        if balance_pack in coupon_data["packs"]:
            discount = coupon_data["discount"]
            logging.info(f"Coupon code '{coupon_code}' is valid for a discount of {discount}% on pack '{balance_pack}'.")
            return True, discount
        else:
            logging.warning(f"Coupon code '{coupon_code}' is not applicable to pack '{balance_pack}'.")
            return False, 0
    else:
        logging.warning(f"Coupon code '{coupon_code}' is invalid.")
        return False, 0

def use_balance(user_uuid):
    """Uses 1 unit of balance from a user's account, if available."""
    try:
        balance = database.get_balance(user_uuid)
        if balance > 0:
            updated_balance = database.update_balance(user_uuid, -1)
            if updated_balance is not None:
                logging.info(f"Used 1 balance for user {user_uuid}. Remaining balance: {updated_balance}")
                return True
            else:
                logging.error(f"Failed to verify updated balance for user {user_uuid}.")
                return False
        else:
            logging.warning(f"Insufficient balance for user {user_uuid}.")
            return False
    except Exception as e:
        logging.error(f"Error in use_balance for user {user_uuid}: {e}")
        return False

def add_balance_manually(user_uuid, balance_to_add):
    """Manually adds a specified balance to a user's account (used for development or testing)."""
    try:
        updated_balance = database.update_balance(user_uuid, balance_to_add)
        if updated_balance is not None:
            logging.info(f"Manually added {balance_to_add} balance to user {user_uuid}. New balance: {updated_balance}")
        else:
            logging.error(f"Failed to add balance to user {user_uuid}.")
    except Exception as e:
        logging.error(f"Error in add_balance_manually for user {user_uuid}: {e}")
