from loguru import logger
import os

# Set up Loguru logger for shared resources
LOG_LEVEL = os.getenv("SHARED_LOG_LEVEL", "INFO")
LOG_FILE = "logs/shared_{time}.log"

# Remove default Loguru handlers to avoid duplicate logs
logger.remove()

# Add a file handler with rotation and structured formatting
logger.add(
    LOG_FILE,
    rotation="1 week",
    level=LOG_LEVEL,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
)

# Add a console handler with color formatting for better readability during development
logger.add(
    lambda msg: print(msg, end=''),
    level=LOG_LEVEL,
    colorize=True,
    format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
)
