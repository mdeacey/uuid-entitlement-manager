import os
from dotenv import load_dotenv
from shared.utils.logging import logger

# Load the admin-specific environment variables
load_dotenv(dotenv_path="./admin/admin.env")

# Example admin-specific utility functions
def validate_admin_access():
    # Admin access validation logic
    logger.info("Admin access validated.")
