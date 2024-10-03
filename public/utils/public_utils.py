import os
from dotenv import load_dotenv
from public.utils.logging import logger

load_dotenv()

# Example public-specific utility functions
def format_currency(amount):
    currency_unit = os.getenv('CURRENCY_UNIT', '$')
    decimals = int(os.getenv('CURRENCY_DECIMALS', 2))
    formatted_amount = f"{currency_unit}{amount:.{decimals}f}"
    logger.info("Formatted currency: {}", formatted_amount)
    return formatted_amount
