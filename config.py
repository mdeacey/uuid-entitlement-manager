import os

class Config:
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'defaultsecretkey')
    DATABASE_FILE = os.getenv('DATABASE_FILE', '/data/database.db')
    FREE_BALANCE = int(os.getenv('FREE_BALANCE', 10))
    FREE_BALANCE_INTERVAL = int(os.getenv('FREE_BALANCE_INTERVAL', 24 * 60 * 60))
    PAYMENT_URL = os.getenv('PAYMENT_URL', '/webhook?user_uuid={user_uuid}&balance={balance}&status=success')
    FLASK_ENV = os.getenv('FLASK_ENV', 'production')
