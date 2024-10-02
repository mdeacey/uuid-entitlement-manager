from flask import Flask, request, render_template, redirect, url_for, make_response, flash
import os
from utils import parse_purchase_packs, parse_coupons, format_currency, get_balance_type, validate_coupon, process_payment, log_env_variables
from dotenv import load_dotenv
from werkzeug.exceptions import BadRequest, InternalServerError
import database
from logger import logger  # Import centralized logger

# Load environment variables
load_dotenv()

# Set up Flask app and secret key
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')

# Log environment variables for reference (excluding sensitive information)
log_env_variables()

# Parse PURCHASE_PACKS and COUPONS from environment variables
PURCHASE_PACKS = parse_purchase_packs('PURCHASE_PACKS')
COUPONS = parse_coupons('COUPONS')
balance_type = get_balance_type()

@app.route('/')
def index():
    try:
        user_uuid = request.cookies.get('user_uuid')
        user_agent_string = request.headers.get('User-Agent')

        if not user_agent_string:
            raise BadRequest("User-Agent is missing.")
        
        hashed_user_agent = database.hash_user_agent(user_agent_string)

        # Create a new user if UUID is missing
        if not user_uuid:
            user_uuid = database.generate_uuid(user_agent=user_agent_string)
            response = make_response(render_template(
                'index.html',
                user_uuid=user_uuid,
                balance=10,
                flask_env=os.getenv('FLASK_ENV'),
                purchase_packs=PURCHASE_PACKS,
                coupons=COUPONS,
                balance_type=balance_type,
                hashed_user_agent=hashed_user_agent,
                format_currency=format_currency
            ))
            response.set_cookie('user_uuid', user_uuid)

            # Log user creation
            logger.info(f"New user created: UUID={user_uuid}, Initial balance=10 {balance_type}")
            flash(f"Welcome! Your new user ID is {user_uuid}.")
            return response

        # Verify if user agent has changed
        stored_user_agent = database.get_user_agent(user_uuid)
        if stored_user_agent is None or stored_user_agent.strip() != hashed_user_agent.strip():
            logger.info(f"User agent change detected for user {user_uuid}. Updating user agent.")
            database.update_user_agent(user_uuid, user_agent_string.strip())
            flash("Browser or device change detected. User agent has been updated.")

        # Retrieve current balance
        balance = database.get_balance(user_uuid)
        logger.info(f"User {user_uuid} accessed. Current balance: {balance} {balance_type}.")

        return render_template(
            'index.html',
            user_uuid=user_uuid,
            balance=balance,
            flask_env=os.getenv('FLASK_ENV'),
            purchase_packs=PURCHASE_PACKS,
            coupons=COUPONS,
            balance_type=balance_type,
            hashed_user_agent=hashed_user_agent,
            format_currency=format_currency
        )
    except BadRequest as e:
        logger.warning(f"Bad request: {e}")
        flash(str(e))
        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Unexpected error in index route: {e}")
        raise InternalServerError("An unexpected error occurred.")

@app.route('/buy_balance', methods=['POST'])
def buy_balance():
    try:
        user_uuid = request.cookies.get('user_uuid')
        balance_pack = request.form.get('balance_pack')
        coupon_code = request.form.get('coupon_code')

        if not user_uuid:
            raise BadRequest("User UUID is missing.")

        if not balance_pack or balance_pack not in PURCHASE_PACKS:
            raise BadRequest(f"Invalid or missing {balance_type} pack selected.")

        discount = 0
        if coupon_code:
            is_valid, discount = validate_coupon(coupon_code, balance_pack)
            if not is_valid:
                flash('Invalid coupon code for the selected pack. Please try again.')
                return redirect(url_for('index'))

        # Calculate final balance to add after discount
        balance_to_add = PURCHASE_PACKS[balance_pack]["size"]
        balance_to_add -= int(balance_to_add * (discount / 100))

        # Update the balance in development mode
        if os.getenv('FLASK_ENV') == 'development':
            updated_balance = database.update_balance(user_uuid, balance_to_add)
            if updated_balance is not None:
                logger.info(f"{balance_to_add} {balance_type} added to user {user_uuid}. New balance: {updated_balance}.")
                flash(f"{balance_to_add} {balance_type} has been added successfully. Current {balance_type}: {updated_balance}.")
            else:
                logger.error(f"Failed to update {balance_type} for user {user_uuid}.")
                flash(f"Failed to update {balance_type}. Please try again.")
            return redirect(url_for('index'))

        # Process payment in production mode
        payment_url = process_payment(user_uuid, balance_pack, discount)
        logger.info(f"Redirecting user {user_uuid} to payment URL.")
        return redirect(payment_url)
    except BadRequest as e:
        logger.warning(f"Bad request in buy_balance: {e}")
        flash(str(e))
        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Unexpected error in buy_balance route: {e}")
        raise InternalServerError("An unexpected error occurred.")

@app.route('/use_balance', methods=['POST'])
def use_balance():
    try:
        user_uuid = request.cookies.get('user_uuid')
        if not user_uuid:
            raise BadRequest("User UUID is missing.")

        success = database.use_balance(user_uuid)
        if success:
            logger.info(f"{balance_type} used successfully for user {user_uuid}.")
            flash(f'{balance_type} used successfully!')
        else:
            logger.warning(f"Insufficient {balance_type} for user {user_uuid}.")
            flash(f'Insufficient {balance_type}. Please buy more or wait for free {balance_type}.')
        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Unexpected error in use_balance route: {e}")
        raise InternalServerError("An unexpected error occurred.")

@app.route('/access_existing_balance', methods=['POST'])
def access_existing_balance():
    try:
        user_uuid = request.form.get('user_uuid')
        if not user_uuid:
            raise BadRequest("User UUID is required.")

        if database.check_uuid_exists(user_uuid):
            balance = database.get_balance(user_uuid)
            logger.info(f"Existing user {user_uuid} accessed. Current balance: {balance} {balance_type}.")
            response = make_response(redirect(url_for('index')))
            response.set_cookie('user_uuid', user_uuid)
            flash(f'Current {balance_type}: {balance}')
            return response
        else:
            logger.warning(f"Invalid UUID {user_uuid} attempted to access.")
            flash('Invalid UUID. Please try again.')
            return redirect(url_for('index'))
    except BadRequest as e:
        logger.warning(f"Bad request in access_existing_balance: {e}")
        flash(str(e))
        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Unexpected error in access_existing_balance route: {e}")
        raise InternalServerError("An unexpected error occurred.")

@app.route('/clear_balance', methods=['POST'])
def clear_balance():
    if os.getenv('FLASK_ENV') == 'development':
        try:
            user_uuid = request.cookies.get('user_uuid')
            if user_uuid:
                database.update_balance(user_uuid, -database.get_balance(user_uuid))
                logger.info(f"Balance for user {user_uuid} cleared to zero.")
                flash(f"Your {balance_type} has been cleared.")
            else:
                logger.warning("User UUID not found for balance clearing.")
                flash("User UUID not found. Please refresh the page and try again.")
        except Exception as e:
            logger.error(f"Error clearing balance for user {user_uuid}: {e}")
            flash(f"An error occurred while clearing your {balance_type}.")
    else:
        flash("This action is not allowed in production.")
    return redirect(url_for('index'))

@app.route('/delete_user_record', methods=['POST'])
def delete_user_record():
    if os.getenv('FLASK_ENV') == 'development':
        try:
            user_uuid = request.cookies.get('user_uuid')
            if user_uuid:
                database.delete_user_record(user_uuid)
                logger.info(f"User record for UUID {user_uuid} deleted successfully.")
                response = make_response(redirect(url_for('index')))
                response.set_cookie('user_uuid', '', expires=0)
                flash("Your user record has been deleted.")
                return response
            else:
                logger.warning("User UUID not found for record deletion.")
                flash("User UUID not found. Please refresh the page and try again.")
        except Exception as e:
            logger.error(f"Error deleting user record for user {user_uuid}: {e}")
            flash("An error occurred while deleting your user record.")
    else:
        flash("This action is not allowed in production.")
    return redirect(url_for('index'))

@app.route('/clear_all_balances', methods=['POST'])
def clear_all_balances():
    if os.getenv('FLASK_ENV') == 'development':
        try:
            database.clear_all_balances()
            logger.info("All user balances cleared to zero.")
            flash(f"All user {balance_type}s have been cleared to zero.")
        except Exception as e:
            logger.error(f"Error clearing all balances: {e}")
            flash(f"An error occurred while clearing all {balance_type}s.")
    else:
        flash("This action is not allowed in production.")
    return redirect(url_for('index'))

@app.route('/delete_all_user_records', methods=['POST'])
def delete_all_user_records():
    if os.getenv('FLASK_ENV') == 'development':
        try:
            database.delete_all_user_records()
            logger.info("All user records deleted successfully.")
            response = make_response(redirect(url_for('index')))
            response.set_cookie('user_uuid', '', expires=0)
            flash("All user records have been deleted.")
            return response
        except Exception as e:
            logger.error(f"Error deleting all user records: {e}")
            flash("An error occurred while deleting all user records.")
    else:
        flash("This action is not allowed in production.")
    return redirect(url_for('index'))

@app.errorhandler(404)
def not_found_error(error):
    logger.warning(f"404 error: {error}")
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"500 error: {error}")
    return render_template('500.html'), 500

if __name__ == '__main__':
    database.init_db()
    app.run(host='0.0.0.0', port=5001, debug=True)
