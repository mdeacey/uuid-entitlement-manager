from flask import Blueprint, render_template
from admin.admin_database import clear_all_balances, delete_all_user_records
from dotenv import load_dotenv
import os

# Load global and admin-specific environment variables
load_dotenv()  # Loads .env
load_dotenv(dotenv_path="./admin/admin.env")  # Loads admin.env

admin_bp = Blueprint('admin', __name__, template_folder='admin/templates', url_prefix='/admin')

@admin_bp.route("/")
def admin_tools_route():
    return render_template("admin/admin.html", balance_type=os.getenv("BALANCE_TYPE", "Credits"))

@admin_bp.route("/clear_all_balances", methods=["POST"])
def clear_all_balances_route():
    clear_all_balances()

@admin_bp.route("/delete_all_user_records", methods=["POST"])
def delete_all_user_records_route():
    delete_all_user_records()