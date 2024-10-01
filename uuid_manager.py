from .uuid_manager import UUIDManager

# Singleton instance for handling all operations
uuid_manager = UUIDManager()

def handle_user_request(user_agent, user_uuid=None, starting_credits=10):
    """
    Get or create a user, automatically manage the UUID, and return their UUID and balance.
    - If user_uuid is provided, it returns the balance.
    - If user_uuid is None, it will create a new user and assign starting credits.
    """
    user_uuid = uuid_manager.get_or_create_user(user_agent, user_uuid, starting_credits)
    balance = uuid_manager.get_balance(user_uuid)
    return user_uuid, balance

def modify_credits(user_uuid, credits):
    """
    Modify credits by adding or subtracting a specific amount.
    - Positive values add credits.
    - Negative values use credits.
    Returns updated balance.
    """
    uuid_manager.add_credits(user_uuid, credits)
    return uuid_manager.get_balance(user_uuid)
