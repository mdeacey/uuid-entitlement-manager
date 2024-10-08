import os
from dotenv import load_dotenv
from flask import Blueprint, request, render_template, redirect, url_for, make_response, flash
from werkzeug.exceptions import BadRequest, InternalServerError
from shared.utils.logging import logger
from shared.utils.shared_utils import format_currency
from public.public_database import (
    hash_user_agent, 
    generate_uuid, 
    add_user_record, 
    get_user_agent, 
    update_user_agent, 
    get_balance, 
    update_balance, 
    use_balance, 
    check_uuid_exists, 
    get_purchase_packs, 
    get_coupons
)

# Load global and public-specific environment variables
load_dotenv()  # Loads .env
load_dotenv(dotenv_path="./public/public.env")  # Loads public.env

public_bp = Blueprint('public', __name__, template_folder='templates')

# Load balance type
balance_type = os.getenv("BALANCE_TYPE", "Credits")

@public_bp.route("/")
def index_route():
    try:
        logger.debug("Accessing index route")
        user_uuid = request.cookies.get("user_uuid")
        user_agent_string = request.headers.get("User-Agent")

        if not user_agent_string:
            raise BadRequest("User-Agent is missing.")

        hashed_user_agent = hash_user_agent(user_agent_string)

        if not user_uuid:
            user_uuid = generate_uuid(user_agent=user_agent_string)
            balance = 10
            add_user_record(user_uuid, hashed_user_agent, balance)
            logger.debug("Generated new UUID: {}", user_uuid)
        else:
            stored_user_agent = get_user_agent(user_uuid)
            if stored_user_agent is None or stored_user_agent.strip() != hashed_user_agent.strip():
                logger.warning("User agent change detected for user {}. Updating user agent.", user_uuid)
                update_user_agent(user_uuid, user_agent_string.strip())
                flash("Browser or device change detected. User agent has been updated.")
            balance = get_balance(user_uuid)

        purchase_packs = get_purchase_packs()
        coupons = get_coupons()

        logger.info("User {} accessed. Current balance: {} {}", user_uuid, balance, balance_type)

        response = make_response(
            render_template(
                "public.html",  # Correct path for the template
                user_uuid=user_uuid,
                balance=balance,
                purchase_packs=purchase_packs,
                coupons=coupons,
                balance_type=balance_type,
                hashed_user_agent=hashed_user_agent,
                format_currency=format_currency,
            )
        )

        if not request.cookies.get("user_uuid"):
            response.set_cookie("user_uuid", user_uuid)
            logger.info("New user created: UUID={}, Initial balance=10 {}", user_uuid, balance_type)
            flash(f"Welcome! Your new user ID is {user_uuid}.")

        return response

    except BadRequest as e:
        logger.warning("Bad request: {}", e)
        flash(str(e))
        return redirect(url_for("public.index_route"))

    except Exception as e:
        logger.exception("Unexpected error in index route: {}", e)
        raise InternalServerError("An unexpected error occurred.")

@public_bp.route("/buy_balance", methods=["POST"])
def buy_balance_route():
    try:
        user_uuid = request.cookies.get("user_uuid")
        balance_pack = request.form.get("balance_pack")
        coupon_code = request.form.get("coupon_code")

        if not user_uuid:
            raise BadRequest("User UUID is missing.")

        purchase_packs = get_purchase_packs()
        if not balance_pack or balance_pack not in purchase_packs:
            raise BadRequest(f"Invalid or missing {balance_type} pack selected.")

        discount = 0
        if coupon_code:
            is_valid, discount = validate_coupon(coupon_code, balance_pack)  # Validate coupon function
            if not is_valid:
                logger.debug("Invalid coupon code {} for pack {}", coupon_code, balance_pack)
                flash("Invalid coupon code for the selected pack. Please try again.")
                return redirect(url_for("public.index_route"))

        balance_to_add = purchase_packs[balance_pack]["size"]
        balance_to_add -= int(balance_to_add * (discount / 100))

        updated_balance = update_balance(user_uuid, balance_to_add)  # Update balance
        if updated_balance is not None:
            logger.success("{} {} added to user {}. New balance: {}.", balance_to_add, balance_type, user_uuid, updated_balance)
            flash(f"{balance_to_add} {balance_type} has been added successfully. Current {balance_type}: {updated_balance}.")
        else:
            logger.error("Failed to update {} for user {}.", balance_type, user_uuid)
            flash(f"Failed to update {balance_type}. Please try again.")
        
        return redirect(url_for("public.index_route"))
    
    except BadRequest as e:
        logger.warning("Bad request in buy_balance: {}", e)
        flash(str(e))
        return redirect(url_for("public.index_route"))
    
    except Exception as e:
        logger.exception("Unexpected error in buy_balance route: {}", e)
        raise InternalServerError("An unexpected error occurred.")

@public_bp.route("/use_balance", methods=["POST"])
def use_balance_route():
    try:
        user_uuid = request.cookies.get("user_uuid")
        if not user_uuid:
            raise BadRequest("User UUID is missing.")

        success = use_balance(user_uuid)  # Use balance
        if success:
            logger.success("{} used successfully for user {}.", balance_type, user_uuid)
            flash(f"{balance_type} used successfully!")
        else:
            logger.warning("Insufficient {} for user {}.", balance_type, user_uuid)
            flash(f"Insufficient {balance_type}. Please buy more or wait for free {balance_type}.")
        
        return redirect(url_for("public.index_route"))
    
    except Exception as e:
        logger.exception("Unexpected error in use_balance route: {}", e)
        raise InternalServerError("An unexpected error occurred.")

@public_bp.route("/access_existing_balance", methods=["POST"])
def access_existing_balance_route():
    try:
        user_uuid = request.form.get("user_uuid")
        if not user_uuid:
            raise BadRequest("User UUID is required.")

        if check_uuid_exists(user_uuid):  # Check if UUID exists
            balance = get_balance(user_uuid)
            logger.info("Existing user {} accessed. Current balance: {} {}", user_uuid, balance, balance_type)
            response = make_response(redirect(url_for("public.index_route")))
            response.set_cookie("user_uuid", user_uuid)
            flash(f"Current {balance_type}: {balance}")
            return response
        else:
            logger.warning("Invalid UUID {} attempted to access.", user_uuid)
            flash("Invalid UUID. Please try again.")
            return redirect(url_for("public.index_route"))
    
    except BadRequest as e:
        logger.warning("Bad request in access_existing_balance: {}", e)
        flash(str(e))
        return redirect(url_for("public.index_route"))
    
    except Exception as e:
        logger.exception("Unexpected error in access_existing_balance route: {}", e)
        raise InternalServerError("An unexpected error occurred.")

@public_bp.route("/clear_balance", methods=["POST"])
def clear_balance_route():
    try:
        user_uuid = request.cookies.get("user_uuid")
        if user_uuid:
            balance_cleared = -get_balance(user_uuid)  # Get balance to clear
            update_balance(user_uuid, balance_cleared)  # Update balance
            logger.info("Balance for user {} cleared to zero.", user_uuid)
            flash(f"Your {balance_type} has been cleared.")
        else:
            logger.warning("User UUID not found for balance clearing.")
            flash("User UUID not found. Please refresh the page and try again.")
    
    except Exception as e:
        logger.exception("Error clearing balance for user {}: {}", user_uuid, e)
        flash(f"An error occurred while clearing your {balance_type}.")
    
    return redirect(url_for("public.index_route"))
