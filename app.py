from flask import Flask, request, render_template, redirect, url_for, make_response, flash
from dotenv import load_dotenv
from user_agents import parse
import logging
import os
import database
from utils import parse_env_list, process_payment, validate_coupon, get_balance_type
from werkzeug.exceptions import BadRequest, InternalServerError

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BALANCE_PACKS = parse_env_list('BALANCE_PACKS')
COUPONS = parse_env_list('COUPONS')

@app.route('/')
def index():
    try:
        user_agent_string = request.headers.get('User-Agent')
        if not user_agent_string:
            raise BadRequest("User-Agent is missing.")

        logging.info(f"User-Agent header: {user_agent_string}")
        user_agent = parse(user_agent_string)

        user_uuid = request.cookies.get('user_uuid')
        if not user_uuid:
            # If no UUID, create a new user and set the cookie
            user_uuid = database.generate_uuid(user_agent=user_agent_string)
            response = make_response(render_template(
                'index.html',
                user_uuid=user_uuid,
                balance=10,
                flask_env=os.getenv('FLASK_ENV'),
                balance_packs=BALANCE_PACKS,
                coupons=COUPONS,
                balance_type=get_balance_type()
            ))
            response.set_cookie('user_uuid', user_uuid)
            return response

        # If UUID exists, verify if user agent has changed
        stored_user_agent = database.get_user_agent(user_uuid)
        if stored_user_agent != user_agent_string:
            # If user agent has changed, update the stored user agent
            logging.info(f"User agent change detected for user {user_uuid}. Updating record.")
            database.update_user_agent(user_uuid, user_agent_string)
            flash("Browser or device change detected. User agent has been updated.")

        balance = database.get_balance(user_uuid)
        return render_template(
            'index.html',
            user_uuid=user_uuid,
            balance=balance,
            flask_env=os.getenv('FLASK_ENV'),
            balance_packs=BALANCE_PACKS,
            coupons=COUPONS,
            balance_type=get_balance_type()
        )
    except BadRequest as e:
        logging.warning(f"Bad request: {e}")
        flash(str(e))
        return redirect(url_for('index'))
    except Exception as e:
        logging.error(f"Error in index: {e}")
        raise InternalServerError("An unexpected error occurred.")

@app.route('/buy_balance', methods=['POST'])
def buy_balance():
    try:
        user_uuid = request.cookies.get('user_uuid')
        balance_pack = request.form.get('balance_pack')
        coupon_code = request.form.get('coupon_code')

        if not user_uuid:
            raise BadRequest("User UUID is missing.")

        if not balance_pack or balance_pack not in BALANCE_PACKS:
            raise BadRequest(f"Invalid or missing {get_balance_type()} pack selected.")

        discount = 0
        if coupon_code:
            is_valid, discount = validate_coupon(coupon_code)
            if not is_valid:
                flash('Invalid coupon code. Please try again.')
                return redirect(url_for('index'))

        if os.getenv('FLASK_ENV') == 'development':
            balance_to_add = int(balance_pack)
            updated_balance = database.update_balance(user_uuid, balance_to_add)
            if updated_balance is not None:
                flash(f"{balance_to_add} {get_balance_type()} has been added successfully. Current {get_balance_type()}: {updated_balance}.")
            else:
                flash(f"Failed to update {get_balance_type()}. Please try again.")
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
def use_balance():
    try:
        user_uuid = request.cookies.get('user_uuid')
        success = database.use_balance(user_uuid)
        if success:
            flash(f'{get_balance_type()} used successfully!')
        else:
            flash(f'Insufficient {get_balance_type()}. Please buy more or wait for free {get_balance_type()}.')
        return redirect(url_for('index'))
    except Exception as e:
        logging.error(f"Error in use_balance: {e}")
        raise InternalServerError("An unexpected error occurred.")

@app.route('/access_existing_balance', methods=['POST'])
def access_existing_balance():
    try:
        user_uuid = request.form.get('user_uuid')
        if not user_uuid:
            raise BadRequest("User UUID is required.")

        if database.check_uuid_exists(user_uuid):
            balance = database.get_balance(user_uuid)
            response = make_response(redirect(url_for('index')))
            response.set_cookie('user_uuid', user_uuid)
            flash(f'Current {get_balance_type()}: {balance}')
            return response
        else:
            flash('Invalid UUID. Please try again.')
            return redirect(url_for('index'))
    except BadRequest as e:
        logging.warning(f"Bad request: {e}")
        flash(str(e))
        return redirect(url_for('index'))
    except Exception as e:
        logging.error(f"Error in access_existing_balance: {e}")
        raise InternalServerError("An unexpected error occurred.")

@app.route('/clear_balance', methods=['POST'])
def clear_balance():
    if os.getenv('FLASK_ENV') == 'development':
        try:
            user_uuid = request.cookies.get('user_uuid')
            if user_uuid:
                database.update_balance(user_uuid, -database.get_balance(user_uuid))
                flash(f"Your {get_balance_type()} has been cleared.")
            else:
                flash("User UUID not found. Please refresh the page and try again.")
        except Exception as e:
            logging.error(f"Error clearing balance for user {user_uuid}: {e}")
            flash(f"An error occurred while clearing your {get_balance_type()}.")
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
                response = make_response(redirect(url_for('index')))
                response.set_cookie('user_uuid', '', expires=0)
                flash("Your user record has been deleted.")
                return response
            else:
                flash("User UUID not found. Please refresh the page and try again.")
        except Exception as e:
            logging.error(f"Error deleting user record for user {user_uuid}: {e}")
            flash("An error occurred while deleting your user record.")
    else:
        flash("This action is not allowed in production.")

    return redirect(url_for('index'))

@app.route('/clear_all_balances', methods=['POST'])
def clear_all_balances():
    if os.getenv('FLASK_ENV') == 'development':
        try:
            database.clear_all_balances()
            flash(f"All user {get_balance_type()}s have been cleared to zero.")
        except Exception as e:
            logging.error(f"Error clearing all balances: {e}")
            flash(f"An error occurred while clearing all {get_balance_type()}s.")
    else:
        flash("This action is not allowed in production.")

    return redirect(url_for('index'))

@app.route('/delete_all_user_records', methods=['POST'])
def delete_all_user_records():
    if os.getenv('FLASK_ENV') == 'development':
        try:
            database.delete_all_user_records()
            logging.info("All user records have been deleted.")

            user_uuid = request.cookies.get('user_uuid')
            response = make_response(redirect(url_for('index')))
            if user_uuid:
                response.set_cookie('user_uuid', '', expires=0)

            flash("All user records have been deleted.")
            return response
        except Exception as e:
            logging.error(f"Error deleting all user records: {e}")
            flash("An error occurred while deleting all user records.")
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
    database.init_db()
    app.run(host='0.0.0.0', port=5001, debug=True)
