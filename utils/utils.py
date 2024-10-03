import os
import ast
from dotenv import load_dotenv
import database
import uuid
import time
from utils.logging import logger

load_dotenv()

# --- Helper Functions ---

def log_sensitive_keys(key, value, sensitive_keys):
    """Logs environment variable values, redacting sensitive keys."""
    if key in sensitive_keys:
        logger.info("{}: [REDACTED]", key)
    else:
        logger.info("{}: {}", key, value)

def validate_env_variable(env_var, error_msg, value_check=lambda x: True):
    """Validates the presence and validity of an environment variable."""
    if env_var not in os.environ:
        logger.error(error_msg)
        raise EnvironmentError(error_msg)
    value = os.getenv(env_var)
    if not value_check(value):
        logger.error(error_msg)
        raise EnvironmentError(error_msg)
    return value

def parse_env_items(env_var, separator=";", key_value_separator=":"):
    """Parses environment variable items into parts."""
    items = os.getenv(env_var, "")
    if items.startswith('"') and items.endswith('"'):
        items = items[1:-1]
    return [item.split(key_value_separator) for item in items.split(separator)] if items else []

def validate_pack_parts(parts):
    """Validates parsed parts of a purchase pack."""
    if len(parts) != 3:
        raise ValueError(f"Invalid format. Expected: PACK_NAME:SIZE:PRICE")
    return parts

def validate_positive_number(value, name):
    """Ensures a value is a positive number."""
    try:
        val = float(value.strip())
        if val <= 0:
            raise ValueError(f"{name} must be a positive number.")
    except ValueError:
        raise ValueError(f"Invalid {name}: '{value}'. Must be a positive number.")
    return val

def log_purchase_pack(pack_name_original, size, balance_type, currency_unit, price):
    """Logs the parsed purchase pack information."""
    logger.info("Purchase Pack Parsed - Pack Name: '{}', Size: {} {}, Price: {}{}", 
                pack_name_original, size, balance_type, currency_unit, price)

def get_applicable_packs(applicable_packs_str):
    """Parses and returns the applicable packs from a string."""
    return [pack.strip().lower() for pack in applicable_packs_str.split(",")]

def log_coupon_validation_result(is_valid, coupon_code, discount, balance_pack):
    """Logs the validation result of the coupon."""
    if is_valid:
        logger.info("Coupon '{}' is valid for {}% discount on '{}'", coupon_code, discount, balance_pack)
    else:
        logger.warning("Coupon '{}' is not applicable to pack '{}'", coupon_code, balance_pack)

def calculate_discounted_amount(balance_amount, discount):
    """Calculates the discounted amount."""
    return max(0, balance_amount - (balance_amount * discount / 100))

def generate_payment_url(user_uuid, formatted_amount):
    """Generates the payment URL for the user."""
    return os.getenv('PAYMENT_URL').format(user_uuid=user_uuid, balance=formatted_amount)

def log_manual_balance_update_result(user_uuid, balance_to_add, updated_balance):
    """Logs the result of manually adding balance to the user."""
    if updated_balance is not None:
        logger.info("Manually added '{}' balance to user '{}'. New balance: {}", balance_to_add, user_uuid, updated_balance)
    else:
        logger.error("Failed to add balance to user '{}'", user_uuid)

# --- Main Functions ---

def load_env_variables():
    sensitive_keys = {'FLASK_SECRET_KEY', 'DATABASE_URL', 'PAYMENT_URL'}
    logger.info("Loading environment variables...")
    for key, value in os.environ.items():
        log_sensitive_keys(key, value, sensitive_keys)

def validate_currency_unit():
    error_msg = "Environment variable 'CURRENCY_UNIT' must be set and be a short string (1-3 characters)."
    return validate_env_variable('CURRENCY_UNIT', error_msg, lambda x: x and len(x) <= 3)

def validate_currency_decimals():
    error_msg = "Environment variable 'CURRENCY_DECIMALS' must be set and be a non-negative integer."
    return validate_env_variable('CURRENCY_DECIMALS', error_msg, lambda x: x.isdigit() and int(x) >= 0)

def validate_balance_type():
    error_msg = "Environment variable 'BALANCE_TYPE' must be set and be a valid string."
    return validate_env_variable('BALANCE_TYPE', error_msg, lambda x: isinstance(x, str))

def parse_and_store_purchase_packs(env_var, currency_unit, balance_type, separator=";", key_value_separator=":"):
    items = parse_env_items(env_var, separator, key_value_separator)
    if items:
        logger.info("Parsing and storing purchase packs from environment variable '{}'...", env_var)
        for parts in items:
            try:
                pack_name_original, size_str, price_str = validate_pack_parts(parts)
                pack_name = pack_name_original.lower()  # Keep lowercase for consistency, but retain original name.
                size = int(validate_positive_number(size_str, "Size"))
                price = float(validate_positive_number(price_str, "Price"))
                # Store in database
                database.add_purchase_pack(pack_name, pack_name_original, size, price, currency_unit)
                logger.info("Stored purchase pack '{}'", pack_name_original)
            except ValueError as e:
                logger.error("Error parsing pack '{}': {}", ":".join(parts), e)
                raise ValueError(f"Invalid format for purchase pack: '{':'.join(parts)}'. Error: {e}")

def parse_and_store_coupons(env_var, purchase_packs, separator=";", key_value_separator=":"):
    items = parse_env_items(env_var, separator, key_value_separator)
    if items:
        logger.info("Parsing and storing coupons from environment variable '{}'...", env_var)
        for parts in items:
            if len(parts) == 3:
                try:
                    coupon_code = parts[0].strip()
                    discount = int(parts[1].strip())
                    if discount < 0 or discount > 100:
                        raise ValueError(f"Discount for coupon '{coupon_code}' must be between 0 and 100.")
                    
                    applicable_packs = get_applicable_packs(parts[2])
                    applicable_packs_original = [purchase_packs[pack]["original_name"] for pack in applicable_packs]

                    # Store in database
                    database.add_coupon(coupon_code, discount, ",".join(applicable_packs_original))
                    logger.info("Stored coupon '{}'", coupon_code)
                except ValueError as e:
                    logger.error("Error parsing coupon '{}': {}", ":".join(parts), e)
                    raise ValueError(f"Invalid format for coupon: '{':'.join(parts)}'. Error: {e}")
            else:
                logger.error("Invalid format for coupon '{}'. Expected format: COUPON_CODE:DISCOUNT:APPLICABLE_PACKS", ":".join(parts))
                raise ValueError(f"Invalid format for coupon: '{':'.join(parts)}'. Expected format: COUPON_CODE:DISCOUNT:APPLICABLE_PACKS")

def format_currency(amount):
    try:
        currency_unit = validate_currency_unit()
        decimals = validate_currency_decimals()
        formatted_amount = f"{currency_unit}{amount:.{decimals}f}"
        logger.info("Formatted currency for amount '{}': '{}'", amount, formatted_amount)
        return formatted_amount
    except Exception as e:
        logger.exception("Error formatting currency for amount '{}': {}", amount, e)
        return str(amount)

def generate_uuid(user_agent, starting_balance=10):
    try:
        logger.info("Generating UUID for new user with user-agent: '{}'", user_agent[:50])
        hashed_user_agent = database.hash_user_agent(user_agent)
        user_uuid = str(uuid.uuid4())
        database.add_user_record(user_uuid, hashed_user_agent, starting_balance)
        logger.info("Generated UUID for new user: '{}', with initial balance: {}", user_uuid, starting_balance)
        return user_uuid
    except Exception as e:
        logger.exception("Error generating UUID for user-agent '{}': {}", user_agent[:50], e)
        return None

def get_balance(user_uuid):
    try:
        logger.info("Retrieving balance for user '{}'", user_uuid)
        last_awarded = database.get_last_awarded(user_uuid)
        current_time = int(time.time())
        free_balance_interval = int(os.getenv('FREE_BALANCE_INTERVAL', 86400))
        free_balance_amount = int(os.getenv('FREE_BALANCE', 10))
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
    try:
        logger.info("Validating coupon '{}' for balance pack '{}'", coupon_code, balance_pack)
        coupons = database.get_coupons()
        coupon_data = coupons.get(coupon_code)
        if coupon_data:
            is_valid = balance_pack in coupon_data["applicable_packs"]
            discount = coupon_data["discount"] if is_valid else 0
            log_coupon_validation_result(is_valid, coupon_code, discount, balance_pack)
            return is_valid, discount
        else:
            logger.warning("Coupon '{}' is invalid.", coupon_code)
            return False, 0
    except Exception as e:
        logger.exception("Error validating coupon '{}' for balance pack '{}': {}", coupon_code, balance_pack, e)
        return False, 0

def process_payment(user_uuid, balance_pack, discount):
    try:
        logger.info("Processing payment for user '{}', balance pack '{}', with discount '{}%'", user_uuid, balance_pack, discount)
        purchase_packs = database.get_purchase_packs()
        if balance_pack not in purchase_packs:
            raise ValueError("Invalid balance pack selected.")
        balance_amount = purchase_packs[balance_pack]["size"]
        final_amount = calculate_discounted_amount(balance_amount, discount)
        formatted_amount = format_currency(final_amount)
        payment_url = generate_payment_url(user_uuid, formatted_amount)
        logger.info("Redirecting user '{}' to payment URL for amount: '{}'", user_uuid, formatted_amount)
        return payment_url
    except Exception as e:
        logger.exception("Error processing payment for user '{}' with balance pack '{}': {}", user_uuid, balance_pack, e)
        raise

def add_balance_manually(user_uuid, balance_to_add):
    try:
        logger.info("Adding '{}' balance manually to user '{}'", balance_to_add, user_uuid)
        updated_balance = database.update_balance(user_uuid, balance_to_add)
        log_manual_balance_update_result(user_uuid, balance_to_add, updated_balance)
    except Exception as e:
        logger.exception("Error adding balance manually for user '{}': {}", user_uuid, e)
