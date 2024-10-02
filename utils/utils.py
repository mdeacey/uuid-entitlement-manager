import os
import ast
from dotenv import load_dotenv
import database
import uuid
import time
from utils.logging import logger

# Load environment variables
load_dotenv()

# Note: Removed logger.add configuration to avoid duplicate logging

def log_env_variables():
    """
    Logs environment variables in a human-readable format, excluding sensitive information.
    """
    sensitive_keys = {'FLASK_SECRET_KEY', 'DATABASE_URL', 'PAYMENT_URL'}
    log_str = "\nENVIRONMENT VARIABLES:\n"

    # Log generic environment variables (excluding sensitive ones)
    for key, value in os.environ.items():
        if key in sensitive_keys:
            log_str += f"{key}: [REDACTED]\n"
        else:
            log_str += f"{key}: {value}\n"

    logger.info(log_str)

# Other utility functions remain the same

def parse_purchase_packs(env_var, separator=";", key_value_separator=":"):
    """
    Parses purchase packs from an environment variable into a dictionary.
    Format: PACK_NAME:APPLICABLE_COUPONS:SIZE; another pack in the same format, and so on...
    """
    items = os.getenv(env_var, "")
    result = {}
    if items:
        for item in items.split(separator):
            parts = item.split(key_value_separator)
            if len(parts) == 3:
                pack_name = parts[0].strip()
                applicable_coupons = ast.literal_eval(parts[1].strip())
                size = int(parts[2].strip())
                result[pack_name] = {
                    "applicable_coupons": applicable_coupons,
                    "size": size
                }
                logger.debug("Parsed pack: {}, Size: {}, Applicable Coupons: {}", pack_name, size, applicable_coupons)
    else:
        logger.warning("No purchase packs found in environment variable: {}", env_var)

    return result

def parse_coupons(env_var, separator=";", key_value_separator=":"):
    """
    Parses coupons from an environment variable into a dictionary.
    Format: COUPON_CODE:DISCOUNT
    """
    items = os.getenv(env_var, "")
    result = {}
    if items:
        for item in items.split(separator):
            parts = item.split(key_value_separator)
            if len(parts) == 2:
                coupon_code = parts[0].strip()
                discount = int(parts[1].strip())
                result[coupon_code] = {
                    "discount": discount
                }
                logger.debug("Parsed coupon: {}, Discount: {}%", coupon_code, discount)
    else:
        logger.warning("No coupons found in environment variable: {}", env_var)

    return result

def get_balance_type():
    """
    Retrieve the customizable term for balance (e.g., Credits, Tokens).
    """
    balance_type = os.getenv('BALANCE_TYPE', 'Credits')
    logger.info("Retrieved balance type: {}", balance_type)
    return balance_type

def format_currency(amount):
    """
    Formats the given amount based on the currency unit and decimal settings.
    """
    try:
        currency_unit = os.getenv('CURRENCY_UNIT', '$')
        decimals = int(os.getenv('CURRENCY_DECIMALS', 2))
        formatted_amount = f"{currency_unit}{amount:.{decimals}f}"
        logger.info("Formatted currency: {}", formatted_amount)
        return formatted_amount
    except Exception as e:
        logger.exception("Error formatting currency for amount {}: {}", amount, e)
        return str(amount)

def generate_uuid(user_agent, starting_balance=10):
    """
    Generates a UUID for a new user and adds them to the database.
    """
    try:
        hashed_user_agent = database.hash_user_agent(user_agent)
        user_uuid = str(uuid.uuid4())
        database.add_user_record(user_uuid, hashed_user_agent, starting_balance)
        logger.info("Generated UUID for new user: {}, with initial balance: {}", user_uuid, starting_balance)
        return user_uuid
    except Exception as e:
        logger.exception("Error generating UUID for user agent '{}': {}", user_agent[:50], e)  # Truncate long user agent strings
        return None

def get_balance(user_uuid):
    """
    Retrieves the current balance for a user, applying free balance if eligible.
    """
    try:
        last_awarded = database.get_last_awarded(user_uuid)
        current_time = int(time.time())
        free_balance_interval = int(os.getenv('FREE_BALANCE_INTERVAL', 86400))
        free_balance_amount = int(os.getenv('FREE_BALANCE', 10))

        # Award free balance if enough time has passed since the last award
        if current_time - last_awarded >= free_balance_interval:
            logger.info("Awarding free balance of {} to user {}", free_balance_amount, user_uuid)
            database.update_balance(user_uuid, free_balance_amount)
            database.update_last_awarded(user_uuid, current_time)

        balance = database.get_balance(user_uuid)
        logger.info("Retrieved balance for user {}: {}", user_uuid, balance)
        return balance
    except Exception as e:
        logger.exception("Error retrieving balance for user {}: {}", user_uuid, e)
        return 0

def validate_coupon(coupon_code, balance_pack):
    """
    Validates a coupon code and checks if it is applicable to the selected balance pack.
    """
    try:
        coupons = parse_coupons('COUPONS')
        coupon_data = coupons.get(coupon_code)
        if coupon_data:
            applicable_packs = parse_purchase_packs('PURCHASE_PACKS')
            if balance_pack in applicable_packs and coupon_code in applicable_packs[balance_pack]["applicable_coupons"]:
                discount = coupon_data["discount"]
                logger.info("Coupon '{}' is valid for {}% discount on '{}'.", coupon_code, discount, balance_pack)
                return True, discount
            else:
                logger.warning("Coupon '{}' is not applicable to pack '{}'.", coupon_code, balance_pack)
                return False, 0
        else:
            logger.warning("Coupon '{}' is invalid.", coupon_code)
            return False, 0
    except Exception as e:
        logger.exception("Error validating coupon '{}' for balance pack '{}': {}", coupon_code, balance_pack, e)
        return False, 0

def process_payment(user_uuid, balance_pack, discount):
    """
    Processes payment for the given balance pack, applying any discount.
    """
    try:
        purchase_packs = parse_purchase_packs('PURCHASE_PACKS')
        if balance_pack not in purchase_packs:
            raise ValueError("Invalid balance pack selected.")

        balance_amount = purchase_packs[balance_pack]["size"]

        # Apply discount if any
        final_amount = max(0, balance_amount - (balance_amount * discount / 100))

        # Format the amount for display
        formatted_amount = format_currency(final_amount)

        # Redirect URL for payment gateway
        payment_url = os.getenv('PAYMENT_URL').format(user_uuid=user_uuid, balance=formatted_amount)
        logger.info("Redirecting user {} to payment URL for amount: {}", user_uuid, formatted_amount)
        return payment_url
    except Exception as e:
        logger.exception("Error processing payment for user {} with balance pack '{}': {}", user_uuid, balance_pack, e)
        raise

def add_balance_manually(user_uuid, balance_to_add):
    """
    Manually adds a specified balance to a user's account (used for development or testing).
    """
    try:
        updated_balance = database.update_balance(user_uuid, balance_to_add)
        if updated_balance is not None:
            logger.info("Manually added {} balance to user {}. New balance: {}", balance_to_add, user_uuid, updated_balance)
        else:
            logger.error("Failed to add balance to user {}.", user_uuid)
    except Exception as e:
        logger.exception("Error adding balance manually for user {}: {}", user_uuid, e)
