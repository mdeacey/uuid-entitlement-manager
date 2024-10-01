from flask import Flask, request, render_template, redirect, url_for, make_response, flash
from utils import generate_uuid, get_balance, update_balance, process_payment, validate_coupon, use_credit, add_credits_manually
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
        user_agent = parse(user_agent_string)

        # Check if UUID exists in cookies
        user_uuid = request.cookies.get('user_uuid')
        if not user_uuid:
            # Generate a UUID and give them 10 initial credits
            user_uuid = generate_uuid(user_agent=user_agent_string)
            response = make_response(render_template('index.html', user_uuid=user_uuid, credits=10))
            response.set_cookie('user_uuid', user_uuid)

            return response

        # Get stored user-agent from the database
        stored_user_agent = database.get_user_agent(user_uuid)

        # Check if the user-agent matches the stored one to prevent credit abuse
        if stored_user_agent and stored_user_agent != user_agent_string:
            flash("Browser or device change detected. Credits will not be reset.")
            return redirect(url_for('index'))

        # Get the current balance, including free credits if applicable
        credits = get_balance(user_uuid)
        return render_template('index.html', user_uuid=user_uuid, credits=credits)
    except Exception as e:
        logging.error(f"Error in index: {e}")
        raise InternalServerError("An unexpected error occurred.")

@app.route('/buy_credits', methods=['POST'])
def buy_credits():
    try:
        user_uuid = request.cookies.get('user_uuid')
        credit_pack = request.form['credit_pack']
        coupon_code = request.form.get('coupon_code')

        if credit_pack not in ["100", "500", "1000", "5000"]:
            raise BadRequest("Invalid credit pack selected.")

        if os.getenv('FLASK_ENV') == 'development':
            # In development, allow manual credit addition without payment
            credits_to_add = int(credit_pack)
            updated_credits = database.update_credits(user_uuid, credits_to_add)
            if updated_credits is not None:
                flash(f"{credits_to_add} credits have been added successfully. Current balance: {updated_credits} credits.")
            else:
                flash("Failed to update credits. Please try again.")
            return redirect(url_for('index'))

        discount = 0
        if coupon_code:
            is_valid, discount = validate_coupon(coupon_code)
            if not is_valid:
                flash('Invalid coupon code. Please try again.')
                return redirect(url_for('index'))

        payment_url = process_payment(user_uuid, credit_pack, discount)
        return redirect(payment_url)
    except BadRequest as e:
        logging.warning(f"Bad request: {e}")
        flash(str(e))
        return redirect(url_for('index'))
    except Exception as e:
        logging.error(f"Error in buy_credits: {e}")
        raise InternalServerError("An unexpected error occurred.")


@app.route('/use_credit', methods=['POST'])
def use_credit_route():
    try:
        user_uuid = request.cookies.get('user_uuid')
        success = use_credit(user_uuid)
        if success:
            flash('Credit used successfully!')
        else:
            flash('Insufficient credits. Please buy more or wait for free credits.')
        return redirect(url_for('index'))
    except Exception as e:
        logging.error(f"Error in use_credit_route: {e}")
        raise InternalServerError("An unexpected error occurred.")

@app.route('/access_existing_credits', methods=['POST'])
def access_existing_credits():
    try:
        user_uuid = request.form['user_uuid']
        if database.check_uuid_exists(user_uuid):
            credit_balance = get_balance(user_uuid)
            response = make_response(redirect(url_for('index')))
            response.set_cookie('user_uuid', user_uuid)
            flash(f'Credit balance: {credit_balance}')
            return response
        else:
            flash('Invalid UUID. Please try again.')
            return redirect(url_for('index'))
    except Exception as e:
        logging.error(f"Error in access_existing_credits: {e}")
        raise InternalServerError("An unexpected error occurred.")
    
@app.route('/reset_all_credits', methods=['POST'])
def reset_all_credits():
    if Config.FLASK_ENV == 'development':
        try:
            database.reset_all_credits()
            flash("All credits have been reset to zero.")
        except Exception as e:
            logging.error(f"Error resetting credits: {e}")
            flash("An error occurred while resetting credits.")
    else:
        flash("This action is not allowed in production.")
    
    return redirect(url_for('index'))

@app.route('/debug_db', methods=['GET'])
def debug_db():
    try:
        conn = sqlite3.connect(Config.DATABASE_FILE)
        c = conn.cursor()
        c.execute('SELECT * FROM users')
        users = c.fetchall()
        return f"Current users in database: {users}", 200
    except sqlite3.Error as e:
        logging.error(f"Database error while debugging: {e}")
        return f"Database error: {e}", 500
    finally:
        conn.close()

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    # Ensure database is initialized before running the server
    database.init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)