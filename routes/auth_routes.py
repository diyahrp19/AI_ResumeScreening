"""
auth_routes.py
--------------
Authentication routes for Flask: Login, Signup, Logout.
Uses the existing auth_db.py for persistence.
On login, loads user data from the database into session.
On logout, only clears session -- never deletes data from DB.
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash

from auth.auth_db import (
    create_user,
    validate_credentials,
    is_username_taken,
    is_email_taken,
)
from database import models

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Render login page and handle login form submission."""
    if session.get("logged_in"):
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username:
            flash("Username is required.", "error")
            return render_template("login.html")

        if not password:
            flash("Password is required.", "error")
            return render_template("login.html")

        user = validate_credentials(username, password)
        if user:
            # Clear any existing session data first
            session.clear()

            # Set auth session
            session["logged_in"] = True
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["email"] = user["email"]

            # Load user's data from database into session
            _load_user_data_into_session(user["id"])

            flash(f"Welcome back, {user['username']}!", "success")
            return redirect(url_for("main.dashboard"))
        else:
            flash("Invalid username or password.", "error")
            return render_template("login.html")

    return render_template("login.html")


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    """Render signup page and handle registration."""
    if session.get("logged_in"):
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        errors = []

        if not username:
            errors.append("Username is required.")
        elif len(username) < 3:
            errors.append("Username must be at least 3 characters.")
        elif is_username_taken(username):
            errors.append("Username already exists.")

        if not email:
            errors.append("Email is required.")
        elif "@" not in email or "." not in email:
            errors.append("Invalid email format.")
        elif is_email_taken(email):
            errors.append("Email already registered.")

        if not password:
            errors.append("Password is required.")
        elif len(password) < 8:
            errors.append("Password must be at least 8 characters.")

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("signup.html", username=username, email=email)

        success = create_user(username=username, email=email, password=password)
        if success:
            flash("Account created successfully! Please sign in.", "success")
            return redirect(url_for("auth.login"))
        else:
            flash("An error occurred. Please try again.", "error")
            return render_template("signup.html", username=username, email=email)

    return render_template("signup.html")


@auth_bp.route("/logout")
def logout():
    """
    Log out the current user.
    ONLY clears the session. NEVER deletes any user data from the database.
    User data persists and will be loaded again on next login.
    """
    session.clear()
    flash("You have been logged out. Your data is safely stored.", "info")
    return redirect(url_for("auth.login"))


def _load_user_data_into_session(user_id: int):
    """Load all user data from the database into the session."""
    import logging
    logger = logging.getLogger(__name__)

    # Load candidates
    try:
        candidates = models.get_candidates_by_user(user_id)
        session["candidates"] = candidates
        logger.info(f"Loaded {len(candidates)} candidates for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to load candidates: {e}")
        session["candidates"] = []

    # Load latest job description
    try:
        job = models.get_latest_job_description(user_id)
        session["job_description"] = job or {}
        logger.info(f"Loaded job description for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to load job description: {e}")
        session["job_description"] = {}

    # Load activity log
    try:
        activities = models.get_activity_log_by_user(user_id, limit=100)
        session["activity_log"] = activities
        logger.info(f"Loaded {len(activities)} activity logs for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to load activity log: {e}")
        session["activity_log"] = []

    # Load report history
    try:
        reports = models.get_report_history_by_user(user_id, limit=50)
        session["report_history"] = reports
        logger.info(f"Loaded {len(reports)} report history entries for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to load report history: {e}")
        session["report_history"] = []

    session.modified = True

