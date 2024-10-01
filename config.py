import os

class Config:
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'defaultsecretkey')
    DATABASE_FILE = os.getenv('DATABASE_FILE', '/data/database.db')  # Changed from 'credits.db' to 'database.db'
    FREE_CREDITS = int(os.getenv('FREE_CREDITS', 10))
    FREE_CREDITS_INTERVAL = int(os.getenv('FREE_CREDITS_INTERVAL', 24 * 60 * 60))
    PAYMENT_URL = os.getenv('PAYMENT_URL', '/webhook?user_uuid={user_uuid}&credits={credits}&status=success')
    FLASK_ENV = os.getenv('FLASK_ENV', 'production')