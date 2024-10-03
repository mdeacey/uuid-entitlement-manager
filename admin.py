from flask import Blueprint, redirect, url_for, flash
from utils.logging import logger
import database

admin_bp = Blueprint('admin', __name__)

@admin_bp.route("/clear_all_balances", methods=["POST"])
def clear_all_balances_route():
    try:
        database.clear_all_balances()
        logger.info("All user balances cleared to zero.")
        flash(f"All user balances have been cleared to zero.")
    except Exception as e:
        logger.exception("Error clearing all balances: {}", e)
        flash("An error occurred while clearing all balances.")
    return redirect(url_for("admin_tools_route"))

@admin_bp.route("/delete_all_user_records", methods=["POST"])
def delete_all_user_records_route():
    try:
        database.delete_all_user_records()
        logger.info("All user records have been successfully deleted.")
        flash("All user records have been deleted.")
    except Exception as e:
        logger.exception("Error deleting all user records: {}", e)
        flash("An error occurred while deleting all user records.")
    return redirect(url_for("admin_tools_route"))

# Admin tools page
@admin_bp.route("/")
def admin_tools_route():
    return render_template("admin.html", balance_type=os.getenv("BALANCE_TYPE", "Credits"))
