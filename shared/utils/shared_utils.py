import os
from dotenv import load_dotenv
from shared.utils.logging import logger

load_dotenv()

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

def format_currency(amount):
    """Formats currency based on shared environment configuration."""
    currency_unit = os.getenv('CURRENCY_UNIT', '$')
    decimals = int(os.getenv('CURRENCY_DECIMALS', 2))
    formatted_amount = f"{currency_unit}{amount:.{decimals}f}"
    logger.info("Formatted currency for amount '{}': '{}'", amount, formatted_amount)
    return formatted_amount
