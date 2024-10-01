import uuid
import time
import database
from config import Config
import logging

FREE_CREDITS = Config.FREE_CREDITS
FREE_CREDITS_INTERVAL = Config.FREE_CREDITS_INTERVAL

def generate_uuid(user_agent, starting_credits=10):
    user_uuid = str(uuid.uuid4())
    database.add_user(user_uuid, user_agent, starting_credits=starting_credits)
    return user_uuid


def get_balance(user_uuid):
    try:
        # Check if the user is eligible for free credits
        last_awarded = database.get_last_awarded(user_uuid)
        current_time = int(time.time())
        if current_time - last_awarded >= FREE_CREDITS_INTERVAL:
            database.update_credits(user_uuid, FREE_CREDITS)
            database.update_last_awarded(user_uuid, current_time)
        return database.get_credits(user_uuid)
    except Exception as e:
        logging.error(f"Error in get_balance: {e}")
        return 0

def update_balance(user_uuid, credits):
    database.update_credits(user_uuid, credits)

def process_payment(user_uuid, credit_pack, discount):
    try:
        credit_amount = {
            "100": 100,
            "500": 500,
            "1000": 1000,
            "5000": 5000
        }.get(credit_pack, 0)

        # Apply discount if any
        final_amount = max(0, credit_amount - discount)

        # Redirect URL for payment gateway
        return Config.PAYMENT_URL.format(user_uuid=user_uuid, credits=final_amount)
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

def use_credit(user_uuid):
    try:
        credits = database.get_credits(user_uuid)
        if credits > 0:
            updated_credits = database.update_credits(user_uuid, -1)
            if updated_credits is not None:
                logging.info(f"Credit used successfully for user {user_uuid}. Remaining credits: {updated_credits}")
                return True
            else:
                logging.error(f"Failed to verify updated credits for user {user_uuid}.")
                return False
        else:
            logging.warning(f"Insufficient credits for user {user_uuid}.")
            return False
    except Exception as e:
        logging.error(f"Error in use_credit: {e}")
        return False

def add_credits_manually(user_uuid, credits_to_add):
    try:
        database.update_credits(user_uuid, credits_to_add)
        logging.info(f"Added {credits_to_add} credits to user {user_uuid}")
    except Exception as e:
        logging.error(f"Error in add_credits_manually: {e}")
