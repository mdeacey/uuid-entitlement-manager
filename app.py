import os
from flask import Flask, render_template, redirect, url_for
from dotenv import load_dotenv
from shared.utils.logging import logger
from admin.admin import admin_bp
from public.public import public_bp
from shared.shared import shared_bp  # Import the shared blueprint
from shared.shared_database import init_db

# Initialize Flask app
app = Flask(__name__)
load_dotenv()  # Load environment variables from .env file

# Register the public, admin, and shared blueprints
app.register_blueprint(public_bp, url_prefix="/")
app.register_blueprint(admin_bp, url_prefix="/admin")
app.register_blueprint(shared_bp)  # Register the shared blueprint

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
