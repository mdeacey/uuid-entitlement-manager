import os
from flask import Flask, redirect, url_for
from dotenv import load_dotenv
from shared.utils.logging import logger
from public.public import public_bp
from shared.shared import shared_bp
from shared.shared_database import init_db

# Initialize Flask app
app = Flask(__name__)
load_dotenv()  # Load environment variables from .env file

# Set the secret key for session management
app.secret_key = os.getenv("FLASK_SECRET_KEY", "your_default_secret_key")  # Ensure a strong secret key is set

# Register the blueprints
app.register_blueprint(public_bp, url_prefix='/')  # Set a prefix if required
app.register_blueprint(shared_bp)

# Initialize the shared database
init_db()

# Error handlers
@app.errorhandler(404)
def not_found_error_route(error):
    logger.warning("404 error: {}", error)
    return redirect(url_for('shared.not_found'))  # Redirect to shared blueprint's not_found route

@app.errorhandler(500)
def internal_error_route(error):
    logger.error("500 error: {}", error)
    return redirect(url_for('shared.internal_error'))  # Redirect to shared blueprint's internal_error route

if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_ENV", "production").lower() == "development"
    app.run(host="0.0.0.0", port=5001, debug=debug_mode)
