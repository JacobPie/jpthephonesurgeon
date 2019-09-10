import os
import smtplib, ssl
import stripe

# TODO ADD MORE COMMENTS and CREATE REQUIREMENTS.TXT

from cs50 import SQL
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, flash, jsonify, redirect, render_template, request, session, abort
from flask_session import Session
from itsdangerous import URLSafeTimedSerializer
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, update, usd

from repair import REPAIR
import re

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

stripe_keys = {
  'secret_key': "sk_test_l2yY1ysutgiwAjg2tDXvYwhp00zwF1qdD6",
  'publishable_key': "pk_test_oqZPEUkhwwlvLgVMjXNrIelr00lhK148yq"
}

stripe.api_key = stripe_keys['secret_key']


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config["SECURITY_PASSWORD_SALT"] = "PIECZYNSKI"
app.config["SECRET_KEY"] = "PIECZYNSKI"




# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///jpthephonesurgeon.db")


# Global variables
devices, brands, models, repairs, colors = [], [], [], [], []
devices_check, brands_check, models_check, repairs_check, colors_check, loggged_in, was_looking_for_repair = False, False, False, False, False, False, False
print("Logged in equals false")
device, brand, model, repair, color, firstname, lastname, email, price, forgot_email, repair_email = "", "", "", "", "", "", "", "", "", "", ""
shipping, ideliver = 0, 0

"""When page is loaded"""
@app.route("/")
def index():
    return render_template("profile/index.html")


prints = {}
captions = {}
"""When they choose to start a repair"""
@app.route("/repair")
@login_required
def repair_page():
    prep_repair()
    global was_looking_for_repair, logged_in
    was_looking_for_repair = False

    if logged_in == True:
        # Reset the repair
        global brands_check, models_check, repairs_check, colors_check, device, brand, model, repair, color
        device, brand, model, repair, color = "", "", "", "", ""
        devices_check, brands_check, models_check, repairs_check, colors_check = False, False, False, False, False
        # Prints the objects
        for piece in REPAIR:
            prints[piece] = REPAIR[piece][1]
            captions[piece] = REPAIR[piece][2]
        return render_template("repair/repair.html", prints=prints, heading=0, captions=captions)
    else:
        was_looking_for_repair = True
        return redirect("/login")


@app.route("/repair_updater", methods=["POST"])
@login_required
def repair_updater():
    if request.method == "POST":
        global brands_check, models_check, repairs_check, colors_check, device, brand, model, repair, color
        prints = {}
        captions = {}
        inputted = request.form.get("input")
        # Loops through the repair.py dictionary
        if colors_check == False:
            repair = inputted
            try:
                check = REPAIR.get(device)[0].get(brand)[0].get(model)[0].get(repair)[4]
            except TypeError:
                # Loops through repairs
                if repairs_check == False:
                    model = inputted
                    try:
                        check = REPAIR.get(device)[0].get(brand)[0].get(model)[0]
                    except TypeError:
                        # Checks models
                        if models_check == False:
                            brand = inputted
                            try:
                                check = REPAIR.get(device)[0].get(brand)[0]
                            except TypeError:
                                # Checks brands
                                if brands_check == False:
                                    device = inputted
                                    check = REPAIR.get(device)[0]
                                    brands_check = True
                                    return update(check, prints, 1, captions)
                            models_check = True
                            return update(check, prints, 2, captions)
                    repairs_check = True
                    return update(check, prints, 3, captions)

            colors_check = True
            return update(check, prints, 4, captions)
        else:
            color = inputted
            return redirect("/confirmation")


"""Login, logout, and register"""


@app.route("/login", methods=["GET", "POST"])
def login():
    print("Logged out in login function")
    global firstname, lastname, email, was_looking_for_repair, logged_in
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        input_email = request.form.get("email")
        password = request.form.get("password")

        # Ensure email was submitted
        if not input_email:
            return apology("must provide email", 403)

        # Ensure password was submitted
        elif not password:
            return apology("must provide password", 403)


        # Query database for email
        rows = db.execute("SELECT * FROM users WHERE split = :split",
                          split=input_email.split('@')[0])

        # Ensure account has been confirmed
        if rows[0]['confirmed'] == 0:
            return apology("account has not been confirmed", 403)

        firstname = rows[0]['firstname']
        lastname = rows[0]['lastname']
        email = rows[0]['email']

        # Ensure email exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], password):
            return apology("invalid email and or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["userid"]

        # Redirect user to their home page
        flash(f"Welcome back, {firstname}!")
        logged_in = True
        if was_looking_for_repair == False:
            was_looking_for_repair = False
            return redirect("/dashboard")
        else:
            was_looking_for_repair = False
            return redirect("/repair")

    else:
        return render_template("auth/login.html")


@app.route("/logout")
@login_required
def logout():
    """Log user out"""
    logged_in = False

    # Forget any user_id
    session.clear()
    print("Logged out in logout function")

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    global firstname, lastname, email, logged_in, was_looking_for_repair, token
    if request.method == "POST":
        firstname = request.form.get("firstname")
        lastname = request.form.get("lastname")
        email = request.form.get("email")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        token = generate_confirmation_token(email)

        # Checks that a first and last name were inputted
        if not firstname:
            return apology("must provide first name", 400)
        elif not lastname:
            return apology("must provide last name", 400)

        # Checks for email
        elif not email:
            return apology("must provide email", 400)

        # Checks that password and confirmation have been inputted
        elif not password or not confirmation:
            return apology("must provide password and confirmation", 400)

        # Checks that password and confirmation are the same
        elif password != confirmation:
            return apology("password and confirmation must be the same", 400)

        # Checks that there is not an account with that email yet
        rows = db.execute("SELECT * FROM users WHERE email = :email",
            email=email)

        if len(rows) >= 1:
            return apology("there is already an account with that email", 400)

        # Sees if they have been referred by anyone
        refers = db.execute("SELECT * FROM refer WHERE email = :email",
            email=email)
        if len(refers) > 0:
            referid = refers[0]['referid']
            db.execute("UPDATE refer SET completed = 1 WHERE referid = :referid", referid=referid)


        db.execute("INSERT INTO users ('firstname', 'lastname', 'hash', 'email', 'split', 'token') VALUES (:firstname, :lastname, :hash, :email, :split, :token)",
            firstname=firstname.capitalize(), lastname=lastname.capitalize(), hash=generate_password_hash(password), email=email, split=email.split('@')[0], token=token)

        userid = db.execute("SELECT userid FROM users WHERE email=:email", email=email)[0]["userid"]

        # confirm email

        # If the user doesn't allow html emails
        text = f"""\
        Hello from JP the Phone Surgeon!
        Please confirm your email by navigating to the link below:
        127.0.0.1:5000/confirm/{token}"""

        send_email(email, token, "JP the Phone Surgeon: Confirm Email", "emails/confirm_email.html", text)
        return render_template("auth/confirm.html", firstname=firstname)
    else:
        return render_template("auth/register.html")


"""Forgot password"""


@app.route("/forgotp", methods=["GET", "POST"])
def forgotp():
    global forgot_email
    if request.method == "POST":
        # Sends email. Right now, it just routes to /
        forgot_email = request.form.get("email")
        rows = db.execute("SELECT * FROM users WHERE email=:email", email=forgot_email)
        if len(rows) == 0:
            flash("There is no account with that email")
            return render_template("auth/forgot-password.html")
        else:
            # Sends email to reset password
            token = generate_confirmation_token(forgot_email)
            db.execute("INSERT INTO forgot ('token') VALUES (:token)", token=token)
            text = f"""\
            Hello from JP the Phone Surgeon!
            To reset your password, navigate to the link below:
            127.0.0.1:5000/forgotp/{token}"""

            send_email(forgot_email, token, "JP the Phone Surgeon: Reset Password", "emails/reset_password.html", text)
        flash("Check your email to reset your password")
        return redirect("/")
    else:
        return render_template("auth/forgot-password.html")


@app.route("/forgotp/<token>")
def reset_password(token):
    global forgot_email
    request_timestamp = db.execute("SELECT timestamp FROM forgot WHERE token=:token", token=token)[0]['timestamp']
    current_timestamp = str(datetime.utcnow())[:19]
    difference = datetime.strptime(request_timestamp, '%Y-%m-%d %H:%M:%S') - datetime.strptime(current_timestamp[:18], '%Y-%m-%d %H:%M:%S')
    if difference >= timedelta(minutes=60):
        # Delete account
        db.execute("DELETE FROM users WHERE token = :token", token=token)
        return render_template("auth/failed.html")

    try:
        confirm = confirm_token(token)
        if confirm == forgot_email:
            db.execute("UPDATE forgot SET used=1 WHERE token=:token", token=token)
            return render_template("auth/reset.html")
    except:
        # Delete account
        db.execute("DELETE FROM forgot WHERE token=:token", token=token)
        flash("Reset failed. Please try again.")
        return render_template("auth/forgot-password.html")


@app.route("/reset_password", methods=["POST"])
def reset():
    global forgot_email
    if request.method == "POST":
        new_password = request.form.get("new_password")
        db.execute("UPDATE users SET hash=:new_password WHERE email=:email", new_password=generate_password_hash(new_password), email=forgot_email)
        return render_template("auth/resetted.html")
    else:
        return apology("Permission Denied: You are not authorized to view this page", 400)


"""Personal Dashboard"""


@app.route("/dashboard")
def dashboard():
    try:
        userid = session["user_id"]
        orders = db.execute("SELECT * FROM orders WHERE userid = :userid", userid=session["user_id"])
        total_repairs = len(orders)
        current_repairs = 0
        for order in orders:
            if order['status'] != "Completed":
                current_repairs += 1
        return render_template("profile/dashboard.html", firstname=firstname, total_repairs=total_repairs, current_repairs=current_repairs)
    except:
        return redirect("/")


@app.route("/confirmation")
@login_required
def confirmation():
    return render_template("repair/order1.html", firstname=firstname, lastname=lastname, email=email)


@app.route("/order_review", methods=["GET", "POST"])
@login_required
def order_review():
    global total
    if request.method == "POST":
        global address, address2, city, state, zipcode, price, shipping
        address = request.form.get("inputAddress")
        # If no Address 2, should return None
        address2 = request.form.get("inputAddress2")
        city = request.form.get("inputCity")
        state = request.form.get("inputState")
        zipcode = request.form.get("inputZip")
        price = REPAIR.get(device)[0].get(brand)[0].get(model)[0].get(repair)[3]
        return render_template("repair/order_review.html", device=device, brand=brand, model=model, repair=repair, color=color, price=(price + shipping))
    else:
        discounts = db.execute("SELECT * FROM refer WHERE refererid = :userid AND used = 0 AND completed = 1",
                                userid=session["user_id"])
        description = color + " " + brand + " " + model + " " + repair
        # UPDATE USED
        coupon = 0
        ldiscounts = len(discounts)
        if ldiscounts > 0:
            coupon = 15
            refer_id = discounts[0]['referid']
            db.execute("UPDATE refer SET used = 1 WHERE used=0 AND referid=:referid", referid=refer_id)
        total = (price + shipping) * ((100 - coupon) / 100)
        ldiscounts -= 1
        if ldiscounts > 0:
            flash(f"You have {ldiscounts} discounts remaining")
        return render_template("repair/payment.html", key=stripe_keys['publishable_key'],
                                email=email, repair=repair, price=price, shipping=shipping, total=total, firstname=firstname,
                                lastname=lastname, coupon=coupon, description=description)


@app.route("/payment")
@login_required
def payment():

    if repair_email == "deliver":
        # Sends receipt
        ideliver = 1
        text = f"""\
        Thank you for your purchase!
        It means a lot to us.
        You have decided to deliver your phone.
        Please drop it off at the scheduled time (you'll get an email in 3-5 business days) at 461 West Angus Road, San Tan Valley, AZ, 85143.
        Any questions? Contact us at 480-439-5389"""

        send_email(email, None, "JP the Phone Surgeon: Thank you for your Purchase!", "emails/receipt2.html", text)
    else:
        ideliver = 0
        # Sends receipt
        text = f"""\
        Thank you for your purchase!
        It means a lot to us.
        In a few days, expect an email from us about scheduling!
        Any questions? Contact us at 480-439-5389"""

        send_email(email, None, "JP the Phone Surgeon: Thank you for your Purchase!", "emails/receipt.html", text)

    # Status: 0 means processing, 1 means part ordered, 2 means repair scheduled, 3 means repair completed
    # iDeliver: 0 means that I have to deliver the phone, 1 means they deliver it
    db.execute("INSERT INTO orders ('userid', 'status', 'model', 'repair', 'color', 'total', 'ideliver') VALUES (:userid, :status, :model, :repair, :color, :total, :ideliver)",
            userid=session['user_id'], status="Processing", model=model, repair=repair, color=color, total=total, ideliver=ideliver)

    # Removes a referral discount from the user's account
    rows = db.execute("SELECT * FROM refer WHERE used = 1 AND refererid = :refererid", refererid=session["user_id"])
    if len(rows) > 0:
        row = rows[0]
        refer_id = row['referid']
        db.execute("UPDATE refer SET used = 0 WHERE used = 1 AND referid = :referid", referid=refer_id)

    return render_template("repair/final.html")


@app.route("/status")
@login_required
def status():
    rows = db.execute("SELECT * FROM orders WHERE userid = :userid AND status != :complete",
            userid=session["user_id"], complete="Complete")
    return render_template("profile/status.html", rows=rows)


@app.route("/refer", methods=["GET", "POST"])
@login_required
def refer():
    if request.method == "POST":
        friend_firstname = request.form.get("firstname").capitalize()
        friend_lastname = request.form.get("lastname").capitalize()
        friend_email = request.form.get("email")
        # SEND EMAIL TO FRIEND
        db.execute("INSERT INTO refer ('refererid', 'firstname', 'lastname', 'email', 'completed', 'used') VALUES (:userid, :firstname, :lastname, :email, :completed, :used)",
                    userid=session["user_id"], firstname=friend_firstname, lastname=friend_lastname, email=friend_email, completed=0, used=0)
        # Sends create account email
        text = f"""\
        A friend has referred you to JP the Phone Surgeon.
        We are the cheapest tech repair service in Arizona!
        We would love to have your business.
        Navigate to the link below to start a repair!
        127.0.0.0:5000/repair"""

        send_email(friend_email, None, "JP the Phone Surgeon: You have been referred!", "emails/referral.html", text)
        return render_template("refer/referred.html", firstname=friend_firstname)
    else:
        return render_template("refer/refer.html")


@app.route('/charge', methods=['POST'])
def charge():
    description = color + " " + brand + " " + model + " " + repair
    response = jsonify('error')
    response.status_code = 500
    try:
        customer = stripe.Customer.create(
            email=email,
            source=request.json['token']
        )
        stripe.Charge.create(
            customer=customer.id,
            amount=int((total * 100)),
            currency='usd',
            description=description
        )
        response = jsonify('success')
        response.status_code = 202
    except stripe.error.StripeError:
        return response
    return response


"""Confirms Email"""
@app.route("/confirm/<token>")
def confirm_email(token):
    registration_timestamp = db.execute("SELECT timestamp FROM users WHERE token=:token", token=token)[0]['timestamp']
    current_timestamp = str(datetime.utcnow())[:19]
    difference = datetime.strptime(current_timestamp[:18], '%Y-%m-%d %H:%M:%S') - datetime.strptime(registration_timestamp, '%Y-%m-%d %H:%M:%S')
    if difference >= timedelta(minutes=60):
        # Delete account
        db.execute("DELETE FROM users WHERE token = :token", token=token)
        return render_template("auth/failed.html")
    try:
        confirm = confirm_token(token)
        if confirm == email:
            db.execute("UPDATE users SET confirmed=1 WHERE token=:token", token=token)
            return render_template("auth/confirmed.html")
    except:
        # Delete account
        db.execute("DELETE FROM users WHERE token = :token", token=token)
        return render_template("auth/failed.html")
    return render_template("auth/failed.html")


# Contact me
@app.route("/contact", methods=["POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        message = request.form.get("message")

        # Sends contact
        text = f"""\
        {name} at {email}:
        {message}"""

        print(message)
        print(email)
        print(name)

        send_email("jacobpieczynski2004@gmail.com", None, "JP the Phone Surgeon: Contact Message", "emails/contact.html", text, None, name, message, email)
    flash("Message sent!")
    return redirect("/dashboard")

"""Auxillary functions"""


@app.route("/check", methods=["GET"])
def check():
    """Return true if email available, else false, in JSON format"""
    email = request.args.get('email')

    names = db.execute("SELECT email FROM users WHERE email=:email", email=email)

    if email and names:
        return jsonify(False)
    elif not names and email:
        return jsonify(True)
    else:
        return jsonify(False)


@app.route("/check_login", methods=["GET"])
def check_login():
    """Return true if email and password match, else false, in JSON format"""
    split = request.args.get('email').split("?")[0].split('@')[0]
    password = request.args.get('email').split("?")[1].split("=")[1]

    names = db.execute("SELECT * FROM users WHERE split=:split", split=split)

    if len(names) > 0:
        check = check_password_hash(names[0]['hash'], password)
    elif len(names) < 1:
        return jsonify(False)

    if split == names[0]['split'] and check == True:
        return jsonify(True)
    else:
        return jsonify(False)


def send_email(email_entered, send_token, subject, template, text, link=None, name=None, contact_message=None, contact_email=None):
    sender_email = "NOTTODAYHAK3R@NICETRY.COM"
    receiver_email = email_entered
    password = "WhatDidISay?NotTodayBru"

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = sender_email
    message["To"] = receiver_email

    print(f"Link: {link}")
    test_html = render_template(template, token=send_token, link=link, name=name, message=contact_message, contact_email=contact_email)

    # Create the plain-text and HTML version of your message

    # Turn these into plain/html MIMEText objects
    part1 = MIMEText(text, "plain")
    part2 = MIMEText(test_html, "html")

    # Add HTML/plain-text parts to MIMEMultipart message
    # The email client will try to render the last part first
    message.attach(part1)
    message.attach(part2)

    print("Message Created...")

    # Create secure connection with server and send email
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        print("Connection Created...")
        server.login(sender_email, password)
        print("Logged in...")
        server.sendmail(
            sender_email, receiver_email, message.as_string()
        )
        print("Message sent!")


@app.route("/zip_check", methods=["GET", "POST"])
def zip_check():
    global shipping, repair_email
    if request.method == "POST":
        shipping = 0
        repair_email = "deliver"
    else:
        """ Return shipping cost """
        zipcode = int(request.args.get('zip'))

        # EXPAND ZIPCODES
        zip_ship = {
            85143: 0,
            85142: 5,
            85140: 5,
            85212: 5,
            85128: 5,
            85147: 12.50,
            85298: 12.50,
            85249: 20,
            85286: 20,
            85297: 20,
            85295: 20,
            85296: 20,
            85234: 20,
            85209: 20,
            85225: 40,
            85121: 40,
            85248: 40
        }
        for key in zip_ship.keys():
            if key == zipcode:
                shipping = zip_ship[zipcode]
                return jsonify(shipping)
            else:
                shipping = 40
        repair_email = "me"
        return jsonify(shipping)


# This gets all the keys and prepares for the repair
def prep_repair():
    for key in REPAIR.keys():
        devices.append(key)
        for device in devices:
            for brand in (REPAIR.get(device)[0]).keys():
                brands.append(brand)
                current_models = (REPAIR.get(device)[0]).get(brand)[0]
                for model in current_models:
                    models.append(model)
                    current_repair = current_models.get(model)[0]
                    for repair in current_repair.keys():
                        repairs.append(repair)
                        try:
                            current_color = current_repair.get(repair)[4]
                        except:
                            break
                        for color in current_color.keys():
                            colors.append(color)


def generate_confirmation_token(email):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    return serializer.dumps(email, salt=app.config['SECURITY_PASSWORD_SALT'])


def confirm_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    try:
        email = serializer.loads(
            token,
            salt=app.config['SECURITY_PASSWORD_SALT'],
            max_age=expiration
        )
    except:
        return False
    return email


if __name__ == "__main__":
    app.run()
