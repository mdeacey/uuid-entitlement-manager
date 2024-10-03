import os
from flask import Flask, render_template
from dotenv import load_dotenv
from shared.utils.logging import logger
from admin.admin import admin_bp
from public.public import public_bp
from shared.shared_database import init_db

# Initialize Flask app
app = Flask(__name__)
load_dotenv()  # Load environment variables from .env file
app.secret_key = os.getenv("FLASK_SECRET_KEY")

# Register the public and admin blueprints
app.register_blueprint(public_bp, url_prefix="/")
app.register_blueprint(admin_bp, url_prefix="/admin")

# Initialize the shared database
init_db()

# Error handlers
@app.errorhandler(404)
def not_found_error_route(error):
    logger.warning("404 error: {}", error)
    return render_template("shared/404.html"), 404

@app.errorhandler(500)
def internal_error_route(error):
    logger.error("500 error: {}", error)
    return render_template("shared/500.html"), 500

if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_ENV", "production").lower() == "development"
    app.run(host="0.0.0.0", port=5001, debug=debug_mode)
