import os
import requests
import urllib.parse

from cs50 import SQL
from flask import flash, redirect, render_template, request, session
from functools import wraps


# Finds SQLite3 database
db = SQL("sqlite:///jpthephonesurgeon.db")


def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("auth/apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def update(check, prints, heading, captions):
    for piece in check:
        photo = check[piece][1]
        captions[piece] = check[piece][2]
        prints[piece] = photo
        if piece == "Apple":
            flash("Coming out with Samsung repair capabilities soon!")

    return render_template("repair/repair.html", prints=prints, heading=heading, captions=captions)


def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"


def schedule(repair, orderid, email):
    link = ""
    if repair == "Screen Repair":
        link = "https://jp-the-phone-surgeon.appointlet.com/s/screen-repair"
    elif repair == "Battery Repair":
        link = "https://jp-the-phone-surgeon.appointlet.com/s/battery-repair"
    elif repair == "Combination":
        link = "https://jp-the-phone-surgeon.appointlet.com/s/combination-repair"

    # If the user doesn't allow html emails
    text = f"""\
    Hello from JP the Phone Surgeon!
    It is time to schedule your repair.
    Please click the link below to schedule your repair.
    {link}"""

    # send_email(email, None, "JP the Phone Surgeon: Schedule your Repair", "emails/scheduling.html", text, link)
    print("WE NEED TO FIX EMAILS")
    db.execute("UPDATE orders SET status='Scheduling' WHERE orderid=:orderid", orderid=orderid)
