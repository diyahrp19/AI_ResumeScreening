"""
reports_routes.py
-----------------
Report generation routes: PDF, Excel, CSV download.
Uses the existing ai.report_generator unchanged.
Also handles "Clear All Data" settings.
"""

import logging
from datetime import datetime

from flask import Blueprint, render_template, session, send_file, flash, redirect, url_for, jsonify, request
import io

from ai.report_generator import generate_pdf, generate_excel, generate_csv
from database import models
from utils.helpers import log_activity

logger = logging.getLogger(__name__)

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")


def _require_login():
    if not session.get("logged_in"):
        return False
    return True


@reports_bp.route("/")
def reports():
    """Render the Reports page."""
    if not _require_login():
        return render_template("login.html")

    candidates = [c for c in session.get("candidates", []) if c.get("scores")]
    job_description = session.get("job_description", {})
    report_history = session.get("report_history", [])

    return render_template(
        "reports.html",
        has_candidates=len(candidates) > 0,
        job_title=job_description.get("title", "Untitled Role"),
        report_history=report_history[-5:],
        username=session.get("username", "User"),
    )


def _log_report(fmt: str, job_title: str):
    """Log a report generation to session history AND database."""
    # Save to session
    report_history = list(session.get("report_history", []))
    report_history.append({
        "format": fmt,
        "job_title": job_title or "Untitled Role",
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "display_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })
    session["report_history"] = report_history
    session.modified = True

    # Save to database
    user_id = session.get("user_id")
    if user_id:
        try:
            models.save_report_history(user_id=user_id, fmt=fmt, job_title=job_title)
        except Exception as e:
            logger.warning(f"Failed to save report history to DB: {e}")

    # Also log to activity feed
    log_activity(session, "report", f"Generated {fmt} report for '{job_title or 'Untitled Role'}'", "", "success")


@reports_bp.route("/download/pdf")
def download_pdf():
    """Generate and download PDF report."""
    if not _require_login():
        return redirect(url_for("auth.login"))

    candidates = [c for c in session.get("candidates", []) if c.get("scores")]
    if not candidates:
        flash("No analyzed candidates available.", "error")
        return redirect(url_for("reports.reports"))

    job = session.get("job_description", {})
    try:
        pdf_bytes = generate_pdf(candidates, job)
        _log_report("PDF", job.get("title", ""))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        logger.info(f"PDF report generated for '{job.get('title', 'Untitled')}' - {len(candidates)} candidates")
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"resume_screening_report_{timestamp}.pdf",
        )
    except Exception as e:
        logger.error(f"Error generating PDF report: {e}", exc_info=True)
        flash(f"Error generating PDF: {str(e)}", "error")
        return redirect(url_for("reports.reports"))


@reports_bp.route("/download/excel")
def download_excel():
    """Generate and download Excel report."""
    if not _require_login():
        return redirect(url_for("auth.login"))

    candidates = [c for c in session.get("candidates", []) if c.get("scores")]
    if not candidates:
        flash("No analyzed candidates available.", "error")
        return redirect(url_for("reports.reports"))

    job = session.get("job_description", {})
    try:
        excel_bytes = generate_excel(candidates, job)
        _log_report("Excel", job.get("title", ""))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        logger.info(f"Excel report generated for '{job.get('title', 'Untitled')}' - {len(candidates)} candidates")
        return send_file(
            io.BytesIO(excel_bytes),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=f"resume_screening_report_{timestamp}.xlsx",
        )
    except Exception as e:
        logger.error(f"Error generating Excel report: {e}", exc_info=True)
        flash(f"Error generating Excel: {str(e)}", "error")
        return redirect(url_for("reports.reports"))


@reports_bp.route("/download/csv")
def download_csv():
    """Generate and download CSV report."""
    if not _require_login():
        return redirect(url_for("auth.login"))

    candidates = [c for c in session.get("candidates", []) if c.get("scores")]
    if not candidates:
        flash("No analyzed candidates available.", "error")
        return redirect(url_for("reports.reports"))

    try:
        csv_bytes = generate_csv(candidates)
        _log_report("CSV", session.get("job_description", {}).get("title", ""))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        logger.info(f"CSV report generated - {len(candidates)} candidates")
        return send_file(
            io.BytesIO(csv_bytes),
            mimetype="text/csv",
            as_attachment=True,
            download_name=f"resume_screening_report_{timestamp}.csv",
        )
    except Exception as e:
        logger.error(f"Error generating CSV report: {e}", exc_info=True)
        flash(f"Error generating CSV: {str(e)}", "error")
        return redirect(url_for("reports.reports"))


# ====================================================================
# SETTINGS / CLEAR DATA
# ====================================================================

@reports_bp.route("/settings")
def settings():
    """Render the Settings page with Clear All Data option."""
    if not _require_login():
        return render_template("login.html")

    return render_template(
        "settings.html",
        username=session.get("username", "User"),
        email=session.get("email", ""),
    )


@reports_bp.route("/clear-data", methods=["POST"])
def clear_data():
    """
    Permanently delete ALL data for the current user.
    This includes:
      - Uploaded resumes (candidates)
      - Candidate analysis results
      - Job descriptions
      - Reports
      - Dashboard data
      - Activity Log

    This action CANNOT be undone.
    """
    if not _require_login():
        return jsonify({"error": "Not logged in"}), 401

    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "User not found"}), 400

    try:
        # Delete all user data from database
        models.clear_user_data(user_id)

        # Clear all data from session
        session["candidates"] = []
        session["job_description"] = {}
        session["activity_log"] = []
        session["report_history"] = []
        session["processed_file_ids"] = []
        session.modified = True

        logger.info(f"All data cleared for user {user_id} ({session.get('username', 'Unknown')})")

        # Log the data clear action (before clearing - this won't persist because we just cleared)
        # Instead, log it directly to DB
        try:
            models.save_activity_log(
                user_id=user_id,
                action="clear_data",
                details="All application data permanently deleted by user",
                candidate_name="",
                status="warning",
            )
        except Exception:
            pass

        flash("All your data has been permanently deleted.", "info")
        # Redirect back to the page the user was on (or dashboard as fallback)
        referrer = request.referrer or url_for("main.dashboard")
        return redirect(referrer)

    except Exception as e:
        logger.error(f"Failed to clear user data: {e}", exc_info=True)
        flash(f"Error clearing data: {str(e)}", "error")
        referrer = request.referrer or url_for("main.dashboard")
        return redirect(referrer)

