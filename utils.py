import uuid
import time
import database
from config import Config
import logging

FREE_BALANCE = Config.FREE_BALANCE
FREE_BALANCE_INTERVAL = Config.FREE_BALANCE_INTERVAL

logging.info(f"Running in Flask environment: {Config.FLASK_ENV}")

def generate_uuid(user_agent, starting_balance=10):
    user_uuid = str(uuid.uuid4())
    database.add_user(user_uuid, user_agent, starting_balance=starting_balance)
    return user_uuid

def get_balance(user_uuid):
    try:
        # Check if the user is eligible for free balance
        last_awarded = database.get_last_awarded(user_uuid)
        current_time = int(time.time())
        if current_time - last_awarded >= FREE_BALANCE_INTERVAL:
            database.update_balance(user_uuid, FREE_BALANCE)
            database.update_last_awarded(user_uuid, current_time)
        return database.get_balance(user_uuid)
    except Exception as e:
        logging.error(f"Error in get_balance: {e}")
        return 0

def update_balance(user_uuid, balance):
    database.update_balance(user_uuid, balance)

def process_payment(user_uuid, balance_pack, discount):
    try:
        balance_amount = {
            "100": 100,
            "500": 500,
            "1000": 1000,
            "5000": 5000
        }.get(balance_pack, 0)

        # Apply discount if any
        final_amount = max(0, balance_amount - discount)

        # Redirect URL for payment gateway
        return Config.PAYMENT_URL.format(user_uuid=user_uuid, balance=final_amount)
    except Exception as e:
        logging.error(f"Error in process_payment: {e}")
        raise

def validate_coupon(coupon_code):
    coupons = {
        "SAVE10": 10,
        "DISCOUNT20": 20,
        "HALFOFF": 50
    }
    return (coupon_code in coupons, coupons.get(coupon_code, 0))

def use_balance(user_uuid):
    try:
        balance = database.get_balance(user_uuid)
        if balance > 0:
            updated_balance = database.update_balance(user_uuid, -1)
            if updated_balance is not None:
                logging.info(f"Balance used successfully for user {user_uuid}. Remaining balance: {updated_balance}")
                return True
            else:
                logging.error(f"Failed to verify updated balance for user {user_uuid}.")
                return False
        else:
            logging.warning(f"Insufficient balance for user {user_uuid}.")
            return False
    except Exception as e:
        logging.error(f"Error in use_balance: {e}")
        return False

def add_balance_manually(user_uuid, balance_to_add):
    try:
        database.update_balance(user_uuid, balance_to_add)
        logging.info(f"Added {balance_to_add} balance to user {user_uuid}")
    except Exception as e:
        logging.error(f"Error in add_balance_manually: {e}")
