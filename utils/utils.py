import os
import ast
from dotenv import load_dotenv
import database
import uuid
import time
from utils.logging import logger

# Load environment variables
load_dotenv()

def load_env_variables():
    """
    Logs environment variables in a human-readable format, excluding sensitive information.
    """
    sensitive_keys = {'FLASK_SECRET_KEY', 'DATABASE_URL', 'PAYMENT_URL'}

    logger.info("Loading environment variables...")

    # Log each environment variable (excluding sensitive ones)
    for key, value in os.environ.items():
        if key in sensitive_keys:
            logger.info("{}: [REDACTED]", key)
        else:
            logger.info("{}: {}", key, value)

def validate_currency_unit():
    """
    Validates that the CURRENCY_UNIT environment variable is properly set.
    """
    logger.info("Validating 'CURRENCY_UNIT' from environment variable...")
    if "CURRENCY_UNIT" not in os.environ:
        logger.error("Environment variable 'CURRENCY_UNIT' is not set.")
        raise EnvironmentError("Environment variable 'CURRENCY_UNIT' must be set.")

    currency_unit = os.getenv("CURRENCY_UNIT")
    if not currency_unit or len(currency_unit) > 3:
        logger.error("Invalid 'CURRENCY_UNIT': '{}' - It must be set and be a short string (1-3 characters).", currency_unit)
        raise EnvironmentError("Environment variable 'CURRENCY_UNIT' must be set and should be a short string (1-3 characters).")
    
    return currency_unit

def validate_currency_decimals():
    """
    Validates that the CURRENCY_DECIMALS environment variable is properly set.
    """
    logger.info("Validating 'CURRENCY_DECIMALS' from environment variable...")
    if "CURRENCY_DECIMALS" not in os.environ:
        logger.error("Environment variable 'CURRENCY_DECIMALS' is not set.")
        raise EnvironmentError("Environment variable 'CURRENCY_DECIMALS' must be set.")

    currency_decimals = os.getenv("CURRENCY_DECIMALS")
    if not currency_decimals.isdigit() or int(currency_decimals) < 0:
        logger.error("Invalid 'CURRENCY_DECIMALS': '{}' - It must be a non-negative integer.", currency_decimals)
        raise EnvironmentError("Environment variable 'CURRENCY_DECIMALS' must be set and must be a non-negative integer.")
    
    return int(currency_decimals)

def validate_balance_type():
    """
    Validates that the BALANCE_TYPE environment variable is properly set.
    """
    logger.info("Validating 'BALANCE_TYPE' from environment variable...")
    if "BALANCE_TYPE" not in os.environ:
        logger.error("Environment variable 'BALANCE_TYPE' is not set.")
        raise EnvironmentError("Environment variable 'BALANCE_TYPE' must be set.")

    balance_type = os.getenv("BALANCE_TYPE")
    if not balance_type or not isinstance(balance_type, str):
        logger.error("Invalid 'BALANCE_TYPE': '{}' - It must be a valid string.", balance_type)
        raise EnvironmentError("Environment variable 'BALANCE_TYPE' must be set and should be a valid string.")
    
    return balance_type


def parse_purchase_packs(env_var, currency_unit, balance_type, separator=";", key_value_separator=":"):
    """
    Parses purchase packs from an environment variable into a dictionary.
    Format: PACK_NAME:SIZE; another pack in the same format, and so on...
    """
    items = os.getenv(env_var, "")
    if items.startswith('"') and items.endswith('"'):
        items = items[1:-1]  # Remove surrounding quotes
    
    result = {}
    if items:
        logger.info("Parsing purchase packs from environment variable '{}'...", env_var)
        for item in items.split(separator):
            parts = item.split(key_value_separator)
            if len(parts) == 2:
                try:
                    pack_name = parts[0].strip()
                    size = int(parts[1].strip())
                    if size <= 0:
                        raise ValueError(f"Size for pack '{pack_name}' must be a positive integer.")

                    result[pack_name] = {
                        "size": size
                    }
                    logger.info("Purchase Pack Parsed - Pack Name: '{}', Size: {} {}", pack_name, size, balance_type)
                except ValueError as e:
                    logger.error("Error parsing pack '{}': {}", item, e)
                    raise ValueError(f"Invalid format for purchase pack: '{item}'. Error: {e}")
            else:
                logger.error("Invalid format for pack '{}'. Expected format: PACK_NAME:SIZE", item)
                raise ValueError(f"Invalid format for purchase pack: '{item}'. Expected format: PACK_NAME:SIZE")
    else:
        logger.warning("No purchase packs found in environment variable '{}'.", env_var)

    return result

def parse_coupons(env_var, currency_unit, separator=";", key_value_separator=":"):
    """
    Parses coupons from an environment variable into a dictionary.
    Format: COUPON_CODE:DISCOUNT:APPLICABLE_PACKS; another coupon in the same format, and so on...
    """
    items = os.getenv(env_var, "")
    if items.startswith('"') and items.endswith('"'):
        items = items[1:-1]  # Remove surrounding quotes

    result = {}
    if items:
        logger.info("Parsing coupons from environment variable '{}'...", env_var)
        for item in items.split(separator):
            parts = item.split(key_value_separator)
            if len(parts) == 3:
                try:
                    coupon_code = parts[0].strip()
                    discount = int(parts[1].strip())
                    if discount < 0 or discount > 100:
                        raise ValueError(f"Discount for coupon '{coupon_code}' must be between 0 and 100.")

                    # Use ast.literal_eval to parse the list of applicable packs
                    applicable_packs_str = parts[2].strip()
                    applicable_packs = ast.literal_eval(applicable_packs_str)
                    if not isinstance(applicable_packs, list):
                        raise ValueError(f"Applicable packs for coupon '{coupon_code}' should be a list.")

                    result[coupon_code] = {
                        "discount": discount,
                        "applicable_packs": applicable_packs
                    }
                    logger.info("Coupon Parsed - Code: '{}', Discount: {}%, Applicable Packs: {}", coupon_code, discount, applicable_packs)
                except (ValueError, SyntaxError) as e:
                    logger.error("Error parsing coupon '{}': {}", item, e)
                    raise ValueError(f"Invalid format for coupon: '{item}'. Error: {e}")
            else:
                logger.error("Invalid format for coupon '{}'. Expected format: COUPON_CODE:DISCOUNT:APPLICABLE_PACKS", item)
                raise ValueError(f"Invalid format for coupon: '{item}'. Expected format: COUPON_CODE:DISCOUNT:APPLICABLE_PACKS")
    else:
        logger.warning("No coupons found in environment variable '{}'.", env_var)

    return result

def format_currency(amount):
    """
    Formats the given amount based on the currency unit and decimal settings.
    """
    try:
        currency_unit = os.getenv('CURRENCY_UNIT', '$')
        decimals = int(os.getenv('CURRENCY_DECIMALS', 2))
        formatted_amount = f"{currency_unit}{amount:.{decimals}f}"
        logger.info("Formatted currency for amount '{}': '{}'", amount, formatted_amount)
        return formatted_amount
    except Exception as e:
        logger.exception("Error formatting currency for amount '{}': {}", amount, e)
        return str(amount)

def generate_uuid(user_agent, starting_balance=10):
    """
    Generates a UUID for a new user and adds them to the database.
    """
    try:
        logger.info("Generating UUID for new user with user-agent: '{}'", user_agent[:50])  # Truncate long user agent strings
        hashed_user_agent = database.hash_user_agent(user_agent)
        user_uuid = str(uuid.uuid4())
        database.add_user_record(user_uuid, hashed_user_agent, starting_balance)
        logger.info("Generated UUID for new user: '{}', with initial balance: {}", user_uuid, starting_balance)
        return user_uuid
    except Exception as e:
        logger.exception("Error generating UUID for user-agent '{}': {}", user_agent[:50], e)
        return None

def get_balance(user_uuid):
    """
    Retrieves the current balance for a user, applying free balance if eligible.
    """
    try:
        logger.info("Retrieving balance for user '{}'", user_uuid)
        last_awarded = database.get_last_awarded(user_uuid)
        current_time = int(time.time())
        free_balance_interval = int(os.getenv('FREE_BALANCE_INTERVAL', 86400))
        free_balance_amount = int(os.getenv('FREE_BALANCE', 10))

        # Award free balance if enough time has passed since the last award
        if current_time - last_awarded >= free_balance_interval:
            logger.info("Awarding free balance of '{}' to user '{}'", free_balance_amount, user_uuid)
            database.update_balance(user_uuid, free_balance_amount)
            database.update_last_awarded(user_uuid, current_time)

        balance = database.get_balance(user_uuid)
        logger.info("Retrieved balance for user '{}': {}", user_uuid, balance)
        return balance
    except Exception as e:
        logger.exception("Error retrieving balance for user '{}': {}", user_uuid, e)
        return 0

def validate_coupon(coupon_code, balance_pack):
    """
    Validates a coupon code and checks if it is applicable to the selected balance pack.
    """
    try:
        logger.info("Validating coupon '{}' for balance pack '{}'", coupon_code, balance_pack)
        coupons = parse_coupons('COUPONS')
        coupon_data = coupons.get(coupon_code)
        if coupon_data:
            applicable_packs = parse_purchase_packs('PURCHASE_PACKS')
            if balance_pack in applicable_packs and coupon_code in applicable_packs[balance_pack]["applicable_coupons"]:
                discount = coupon_data["discount"]
                logger.info("Coupon '{}' is valid for {}% discount on '{}'", coupon_code, discount, balance_pack)
                return True, discount
            else:
                logger.warning("Coupon '{}' is not applicable to pack '{}'", coupon_code, balance_pack)
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
        logger.info("Processing payment for user '{}', balance pack '{}', with discount '{}%'", user_uuid, balance_pack, discount)
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
        logger.info("Redirecting user '{}' to payment URL for amount: '{}'", user_uuid, formatted_amount)
        return payment_url
    except Exception as e:
        logger.exception("Error processing payment for user '{}' with balance pack '{}': {}", user_uuid, balance_pack, e)
        raise

def add_balance_manually(user_uuid, balance_to_add):
    """
    Manually adds a specified balance to a user's account (used for development or testing).
    """
    try:
        logger.info("Adding '{}' balance manually to user '{}'", balance_to_add, user_uuid)
        updated_balance = database.update_balance(user_uuid, balance_to_add)
        if updated_balance is not None:
            logger.info("Manually added '{}' balance to user '{}'. New balance: {}", balance_to_add, user_uuid, updated_balance)
        else:
            logger.error("Failed to add balance to user '{}'", user_uuid)
    except Exception as e:
        logger.exception("Error adding balance manually for user '{}': {}", user_uuid, e)
