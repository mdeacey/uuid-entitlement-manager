from flask import Flask, request, render_template, redirect, url_for, make_response, flash
from utils import generate_uuid, get_balance, update_balance, process_payment, validate_coupon, use_balance
import database
from config import Config
from werkzeug.exceptions import BadRequest, InternalServerError
import logging
import os
from user_agents import parse

app = Flask(__name__)
app.secret_key = Config.SECRET_KEY

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@app.route('/')
def index():
    try:
        # Extract user-agent from the request
        user_agent_string = request.headers.get('User-Agent')
        logging.info(f"User-Agent header: {user_agent_string}")
        user_agent = parse(user_agent_string)

        # Check if UUID exists in cookies
        user_uuid = request.cookies.get('user_uuid')
        if not user_uuid:
            # Generate a UUID and give them initial balance
            user_uuid = generate_uuid(user_agent=user_agent_string)
            response = make_response(render_template('index.html', user_uuid=user_uuid, balance=10, flask_env=os.getenv('FLASK_ENV')))
            response.set_cookie('user_uuid', user_uuid)
            return response

        # Get stored user-agent from the database
        stored_user_agent = database.get_user_agent(user_uuid)
        logging.info(f"Retrieved stored user-agent for user {user_uuid}: {stored_user_agent}")

        # Check if the user-agent matches the stored one to prevent balance abuse
        if stored_user_agent and stored_user_agent != user_agent_string:
            flash("Browser or device change detected. Balance will not be reset.")
            return redirect(url_for('index'))

        # Get the current balance, including free balance if applicable
        balance = get_balance(user_uuid)
        return render_template('index.html', user_uuid=user_uuid, balance=balance, flask_env=os.getenv('FLASK_ENV'))
    except Exception as e:
        logging.error(f"Error in index: {e}")
        raise InternalServerError("An unexpected error occurred.")

@app.route('/buy_balance', methods=['POST'])
def buy_balance():
    try:
        user_uuid = request.cookies.get('user_uuid')
        balance_pack = request.form['balance_pack']
        coupon_code = request.form.get('coupon_code')

        if balance_pack not in ["100", "500", "1000", "5000"]:
            raise BadRequest("Invalid balance pack selected.")

        if os.getenv('FLASK_ENV') == 'development':
            # In development, allow manual balance addition without payment
            balance_to_add = int(balance_pack)
            updated_balance = database.update_balance(user_uuid, balance_to_add)
            if updated_balance is not None:
                flash(f"{balance_to_add} balance has been added successfully. Current balance: {updated_balance}.")
            else:
                flash("Failed to update balance. Please try again.")
            return redirect(url_for('index'))

        discount = 0
        if coupon_code:
            is_valid, discount = validate_coupon(coupon_code)
            if not is_valid:
                flash('Invalid coupon code. Please try again.')
                return redirect(url_for('index'))

        payment_url = process_payment(user_uuid, balance_pack, discount)
        return redirect(payment_url)
    except BadRequest as e:
        logging.warning(f"Bad request: {e}")
        flash(str(e))
        return redirect(url_for('index'))
    except Exception as e:
        logging.error(f"Error in buy_balance: {e}")
        raise InternalServerError("An unexpected error occurred.")

@app.route('/use_balance', methods=['POST'])
def use_balance_route():
    try:
        user_uuid = request.cookies.get('user_uuid')
        success = use_balance(user_uuid)
        if success:
            flash('Balance used successfully!')
        else:
            flash('Insufficient balance. Please buy more or wait for free balance.')
        return redirect(url_for('index'))
    except Exception as e:
        logging.error(f"Error in use_balance_route: {e}")
        raise InternalServerError("An unexpected error occurred.")

@app.route('/access_existing_balance', methods=['POST'])
def access_existing_balance():
    try:
        user_uuid = request.form['user_uuid']
        if database.check_uuid_exists(user_uuid):
            balance = get_balance(user_uuid)
            response = make_response(redirect(url_for('index')))
            response.set_cookie('user_uuid', user_uuid)
            flash(f'Balance: {balance}')
            return response
        else:
            flash('Invalid UUID. Please try again.')
            return redirect(url_for('index'))
    except Exception as e:
        logging.error(f"Error in access_existing_balance: {e}")
        raise InternalServerError("An unexpected error occurred.")

@app.route('/reset_balance', methods=['POST'])
def reset_balance():
    if Config.FLASK_ENV == 'development':
        try:
            user_uuid = request.cookies.get('user_uuid')
            if user_uuid:
                database.update_balance(user_uuid, -database.get_balance(user_uuid))  # Set balance to zero
                flash("All your balance has been reset.")
            else:
                flash("User UUID not found. Please refresh the page and try again.")
        except Exception as e:
            logging.error(f"Error resetting balance for user {user_uuid}: {e}")
            flash("An error occurred while resetting your balance.")
    else:
        flash("This action is not allowed in production.")

    return redirect(url_for('index'))

@app.route('/reset_all_balance', methods=['POST'])
def reset_all_balance():
    if Config.FLASK_ENV == 'development':
        try:
            database.reset_all_balance()
            flash("All balance has been reset to zero.")
        except Exception as e:
            logging.error(f"Error resetting all balance: {e}")
            flash("An error occurred while resetting all balance.")
    else:
        flash("This action is not allowed in production.")

    return redirect(url_for('index'))

@app.route('/reset_all_sessions', methods=['POST'])
def reset_all_sessions():
    if Config.FLASK_ENV == 'development':
        try:
            database.reset_all_users()
            flash("All sessions have been removed. A new UUID will be assigned on the next visit.")
        except Exception as e:
            logging.error(f"Error resetting all sessions: {e}")
            flash("An error occurred while removing all sessions.")
    else:
        flash("This action is not allowed in production.")

    return redirect(url_for('index'))

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    # Ensure database is initialized before running the server
    database.init_db()
    app.run(host='0.0.0.0', port=5001, debug=True)
