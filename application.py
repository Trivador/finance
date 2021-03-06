import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


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
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    stocks = db.execute("SELECT ticker, SUM(spent), SUM(number_stocks) FROM purchases WHERE transaction_id = ? GROUP BY ticker", session["user_id"])
    tickers = []
    total_price = []
    owned = []
    for i in range(len(stocks)):
        tickers.append(stocks[i]["ticker"])
        total_price.append(stocks[i]["SUM(spent)"])
        owned.append(stocks[i]["SUM(number_stocks)"])
    currentvalue = []
    for value in tickers:
        jsonfile = lookup(value)
        currentvalue.append(jsonfile["price"])
    benefice = []
    for i in range(len(currentvalue)):
        result = (owned[i] * currentvalue[i]) - total_price[i]
        benefice.append(result)
    exes = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
    money = exes[0]["cash"]
    totalbenefice = sum(benefice) + money + sum(total_price)
    name = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])
    return render_template("main.html", name = name[0]["username"], money = usd(money), nbr = len(tickers), ticker = tickers, invested = total_price, shares = owned, currentpriceticker = currentvalue, benefice = benefice, totalbenefice = usd(totalbenefice))


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        jsonfile = lookup(request.form.get("symbol"))
        shares = request.form.get("shares")
        if jsonfile == None:
            return apology("Wrong ticker")
        if not shares.isdigit() or int(shares) == 0:
            return apology("Invalid number of shares")
        price_of_stock = float(jsonfile["price"])
        price_to_pay = price_of_stock * int(shares)
        cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
        current_cash = cash[0]["cash"]
        if current_cash < price_to_pay:
            return apology("Not enought money")
        # Updates users cash
        db.execute("UPDATE users SET cash = ? WHERE id = ?", current_cash - price_to_pay, session["user_id"])
        # TODO: Create UNIQUE sql
        db.execute("INSERT INTO purchases (transaction_id, ticker, price, time, number_stocks, spent) VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?, ?)", session["user_id"], jsonfile["symbol"], price_of_stock, int(shares), price_of_stock * int(shares))
        return redirect("/")
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    return apology("TODO")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        jsonfile = lookup(request.form.get("symbol"))
        if jsonfile == None:
            return apology("Wrong ticker")
        return render_template("quoted.html", name = jsonfile["name"], ticker = jsonfile["symbol"], price = usd(jsonfile["price"]))
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    # Post form
    if request.method == "POST":
        # No username
        if not request.form.get("username"):
            return apology("must provide username", 403)
        # Not unique username
        usernamecheck = db.execute("SELECT COUNT(username) FROM users WHERE username = ?", request.form.get("username"))
        if usernamecheck[0]["COUNT(username)"] != 0:
            return apology("must provide unique username", 403)
        # Not 2 passwords
        if not request.form.get("password") or not request.form.get("confirmation"):
            return apology("Must provide both passwords", 403)
        # No match
        if request.form.get("password") != request.form.get("confirmation"):
            return apology("Both passwords must match", 403)
        
        # Add input to database
        db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", request.form.get("username"), generate_password_hash(request.form.get("password")))
        return redirect("/")
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    return apology("TODO")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
