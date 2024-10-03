from flask import Blueprint, render_template, redirect, url_for, flash
from admin.utils.logging import logger
import admin.database as database
from dotenv import load_dotenv
import os

# Load global and admin-specific environment variables
load_dotenv()  # Loads .env
load_dotenv(dotenv_path="./admin/admin.env")  # Loads admin.env

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
@admin_bp.route("/")
def admin_tools_route():
    return render_template("admin.html", balance_type=os.getenv("BALANCE_TYPE", "Credits"))

@admin_bp.route("/clear_all_balances", methods=["POST"])
def clear_all_balances_route():
    try:
        database.clear_all_balances()
        logger.info("All user balances cleared to zero.")
        flash("All user balances have been cleared to zero.")
    except Exception as e:
        logger.exception("Error clearing all balances: {}", e)
        flash("An error occurred while clearing all balances.")
    return redirect(url_for("admin.admin_tools_route"))

@admin_bp.route("/delete_all_user_records", methods=["POST"])
def delete_all_user_records_route():
    try:
        database.delete_all_user_records()
        logger.info("All user records have been successfully deleted.")
        flash("All user records have been deleted.")
    except Exception as e:
        logger.exception("Error deleting all user records: {}", e)
        flash("An error occurred while deleting all user records.")
    return redirect(url_for("admin.admin_tools_route"))
