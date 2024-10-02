import os
from flask import Flask, request, render_template, redirect, url_for, make_response, flash
from utils.utils import (
    load_env_variables,
    validate_currency_unit, 
    validate_currency_decimals,
    validate_balance_type,
    parse_and_store_purchase_packs,
    parse_and_store_coupons,
    format_currency,
    validate_coupon,
    process_payment,
)
from dotenv import load_dotenv
from werkzeug.exceptions import BadRequest, InternalServerError
from utils.logging import logger
import database

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

load_dotenv()

if os.getenv("WERKZEUG_RUN_MAIN") is None:
    load_env_variables()
    database.init_db()

currency_unit = validate_currency_unit()
currency_decimals = validate_currency_decimals()
balance_type = validate_balance_type()

if os.getenv("WERKZEUG_RUN_MAIN") is None:
    parse_and_store_purchase_packs("PURCHASE_PACKS", currency_unit, balance_type)
    parse_and_store_coupons("COUPONS", database.get_purchase_packs())

purchase_packs = database.get_purchase_packs()
coupons = database.get_coupons()

@app.route("/")
def index_route():
    try:
        user_uuid = request.cookies.get("user_uuid")
        user_agent_string = request.headers.get("User-Agent")

        if not user_agent_string:
            raise BadRequest("User-Agent is missing.")

        hashed_user_agent = database.hash_user_agent(user_agent_string)

        if not user_uuid:
            user_uuid = database.generate_uuid(user_agent=user_agent_string)
            response = make_response(
                render_template(
                    "index.html",
                    user_uuid=user_uuid,
                    balance=10,
                    flask_env=os.getenv("FLASK_ENV"),
                    purchase_packs=purchase_packs,
                    coupons=coupons,
                    balance_type=balance_type,
                    hashed_user_agent=hashed_user_agent,
                    format_currency=format_currency,
                )
            )
            response.set_cookie("user_uuid", user_uuid)
            logger.info("New user created: UUID={}, Initial balance=10 {}", user_uuid, balance_type)
            flash(f"Welcome! Your new user ID is {user_uuid}.")
            return response

        stored_user_agent = database.get_user_agent(user_uuid)
        if stored_user_agent is None or stored_user_agent.strip() != hashed_user_agent.strip():
            logger.warning("User agent change detected for user {}. Updating user agent.", user_uuid)
            database.update_user_agent(user_uuid, user_agent_string.strip())
            flash("Browser or device change detected. User agent has been updated.")

        balance = database.get_balance(user_uuid)
        logger.info("User {} accessed. Current balance: {} {}", user_uuid, balance, balance_type)

        return render_template(
            "index.html",
            user_uuid=user_uuid,
            balance=balance,
            flask_env=os.getenv("FLASK_ENV"),
            purchase_packs=purchase_packs,
            coupons=coupons,
            balance_type=balance_type,
            hashed_user_agent=hashed_user_agent,
            format_currency=format_currency,
        )
    except BadRequest as e:
        logger.warning("Bad request: {}", e)
        flash(str(e))
        return redirect(url_for("index_route"))
    except Exception as e:
        logger.exception("Unexpected error in index route: {}", e)
        raise InternalServerError("An unexpected error occurred.")

@app.route("/buy_balance", methods=["POST"])
def buy_balance_route():
    try:
        user_uuid = request.cookies.get("user_uuid")
        balance_pack = request.form.get("balance_pack")
        coupon_code = request.form.get("coupon_code")

        if not user_uuid:
            raise BadRequest("User UUID is missing.")

        if not balance_pack or balance_pack not in purchase_packs:
            raise BadRequest(f"Invalid or missing {balance_type} pack selected.")

        discount = 0
        if coupon_code:
            is_valid, discount = validate_coupon(coupon_code, balance_pack)
            if not is_valid:
                logger.debug("Invalid coupon code {} for pack {}", coupon_code, balance_pack)
                flash("Invalid coupon code for the selected pack. Please try again.")
                return redirect(url_for("index_route"))

        balance_to_add = purchase_packs[balance_pack]["size"]
        balance_to_add -= int(balance_to_add * (discount / 100))

        if os.getenv("FLASK_ENV") == "development":
            updated_balance = database.update_balance(user_uuid, balance_to_add)
            if updated_balance is not None:
                logger.success("{} {} added to user {}. New balance: {}.", balance_to_add, balance_type, user_uuid, updated_balance)
                flash(f"{balance_to_add} {balance_type} has been added successfully. Current {balance_type}: {updated_balance}.")
            else:
                logger.error("Failed to update {} for user {}.", balance_type, user_uuid)
                flash(f"Failed to update {balance_type}. Please try again.")
            return redirect(url_for("index_route"))

        payment_url = process_payment(user_uuid, balance_pack, discount)
        logger.info("Redirecting user {} to payment URL.", user_uuid)
        return redirect(payment_url)
    except BadRequest as e:
        logger.warning("Bad request in buy_balance: {}", e)
        flash(str(e))
        return redirect(url_for("index_route"))
    except Exception as e:
        logger.exception("Unexpected error in buy_balance route: {}", e)
        raise InternalServerError("An unexpected error occurred.")

@app.route("/use_balance", methods=["POST"])
def use_balance_route():
    try:
        user_uuid = request.cookies.get("user_uuid")
        if not user_uuid:
            raise BadRequest("User UUID is missing.")

        success = database.use_balance(user_uuid)
        if success:
            logger.success("{} used successfully for user {}.", balance_type, user_uuid)
            flash(f"{balance_type} used successfully!")
        else:
            logger.warning("Insufficient {} for user {}.", balance_type, user_uuid)
            flash(f"Insufficient {balance_type}. Please buy more or wait for free {balance_type}.")
        return redirect(url_for("index_route"))
    except Exception as e:
        logger.exception("Unexpected error in use_balance route: {}", e)
        raise InternalServerError("An unexpected error occurred.")

@app.route("/access_existing_balance", methods=["POST"])
def access_existing_balance_route():
    try:
        user_uuid = request.form.get("user_uuid")
        if not user_uuid:
            raise BadRequest("User UUID is required.")

        if database.check_uuid_exists(user_uuid):
            balance = database.get_balance(user_uuid)
            logger.info("Existing user {} accessed. Current balance: {} {}", user_uuid, balance, balance_type)
            response = make_response(redirect(url_for("index_route")))
            response.set_cookie("user_uuid", user_uuid)
            flash(f"Current {balance_type}: {balance}")
            return response
        else:
            logger.warning("Invalid UUID {} attempted to access.", user_uuid)
            flash("Invalid UUID. Please try again.")
            return redirect(url_for("index_route"))
    except BadRequest as e:
        logger.warning("Bad request in access_existing_balance: {}", e)
        flash(str(e))
        return redirect(url_for("index_route"))
    except Exception as e:
        logger.exception("Unexpected error in access_existing_balance route: {}", e)
        raise InternalServerError("An unexpected error occurred.")

@app.route("/clear_balance", methods=["POST"])
def clear_balance_route():
    if os.getenv("FLASK_ENV") == "development":
        try:
            user_uuid = request.cookies.get("user_uuid")
            if user_uuid:
                balance_cleared = -database.get_balance(user_uuid)
                database.update_balance(user_uuid, balance_cleared)
                logger.info("Balance for user {} cleared to zero.", user_uuid)
                flash(f"Your {balance_type} has been cleared.")
            else:
                logger.warning("User UUID not found for balance clearing.")
                flash("User UUID not found. Please refresh the page and try again.")
        except Exception as e:
            logger.exception("Error clearing balance for user {}: {}", user_uuid, e)
            flash(f"An error occurred while clearing your {balance_type}.")
    else:
        flash("This action is not allowed in production.")
    return redirect(url_for("index_route"))

@app.route("/delete_user_record", methods=["POST"])
def delete_user_record_route():
    if os.getenv("FLASK_ENV") == "development":
        try:
            user_uuid = request.cookies.get("user_uuid")
            if user_uuid:
                database.delete_user_record(user_uuid)
                logger.info("User record for UUID {} deleted successfully.", user_uuid)
                response = make_response(redirect(url_for("index_route")))
                response.set_cookie("user_uuid", "", expires=0)
                flash("Your user record has been deleted.")
                return response
            else:
                logger.warning("User UUID not found for record deletion.")
                flash("User UUID not found. Please refresh the page and try again.")
        except Exception as e:
            logger.exception("Error deleting user record for user {}: {}", user_uuid, e)
            flash("An error occurred while deleting your user record.")
    else:
        flash("This action is not allowed in production.")
    return redirect(url_for("index_route"))

@app.route("/clear_all_balances", methods=["POST"])
def clear_all_balances_route():
    if os.getenv("FLASK_ENV") == "development":
        try:
            database.clear_all_balances()
            logger.info("All user balances cleared to zero.")
            flash(f"All user {balance_type}s have been cleared to zero.")
        except Exception as e:
            logger.exception("Error clearing all balances: {}", e)
            flash(f"An error occurred while clearing all {balance_type}s.")
    else:
        flash("This action is not allowed in production.")
    return redirect(url_for("index_route"))

@app.route("/delete_all_user_records", methods=["POST"])
def delete_all_user_records_route():
    if os.getenv("FLASK_ENV") == "development":
        try:
            database.delete_all_user_records()
            logger.info("All user records have been successfully deleted.")
            response = make_response(redirect(url_for("index_route")))
            response.set_cookie("user_uuid", "", expires=0)
            flash("All user records have been deleted.")
            return response
        except Exception as e:
            logger.exception("Error deleting all user records: {}", e)
            flash("An error occurred while deleting all user records.")
    else:
        flash("This action is not allowed in production.")
    return redirect(url_for("index_route"))

@app.errorhandler(404)
def not_found_error_route(error):
    logger.warning("404 error: {}", error)
    return render_template("404.html"), 404

@app.errorhandler(500)
def internal_error_route(error):
    logger.error("500 error: {}", error)
    return render_template("500.html"), 500

if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_ENV", "production").lower() == "development"
    app.run(host="0.0.0.0", port=5001, debug=debug_mode)
