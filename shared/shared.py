# shared/shared.py
from flask import Blueprint, render_template

shared_bp = Blueprint('shared', __name__, template_folder='templates')

@shared_bp.route("/404")
def not_found():
    return render_template("404.html"), 404

@shared_bp.route("/500")
def internal_error():
    return render_template("500.html"), 500
