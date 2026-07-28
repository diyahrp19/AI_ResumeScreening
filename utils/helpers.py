"""
helpers.py
----------
Shared utilities for the Flask-based AI Resume Screening System.

Contains:
  - Activity logging helper for session-based and DB activity tracking
  - Logging utility functions
  - Small formatting helpers for the dashboard
"""

import logging
from datetime import datetime
from typing import Dict, List


# Get logger for this module
logger = logging.getLogger(__name__)


def log_activity(session, action: str, details: str, candidate_name: str = "", status: str = ""):
    """
    Log an activity entry to the session's activity_log list AND to the database.
    Activities are stored in chronological order (newest last).

    Args:
        session: Flask session object
        action: Type of action (upload, analyze, shortlist, reject, report, delete)
        details: Human-readable description of what happened
        candidate_name: Name of the candidate involved (optional)
        status: Status of the action (success, warning, error) (optional)
    """
    try:
        # Save to session
        activity_log = list(session.get("activity_log", []))
        entry = {
            "action": action,
            "details": details,
            "candidate_name": candidate_name,
            "status": status or "success",
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "display_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        activity_log.append(entry)
        # Keep only last 100 activities to prevent session bloating
        if len(activity_log) > 100:
            activity_log = activity_log[-100:]
        session["activity_log"] = activity_log
        session.modified = True

        # Also save to database if user is logged in
        user_id = session.get("user_id")
        if user_id:
            try:
                from database import models
                models.save_activity_log(
                    user_id=user_id,
                    action=action,
                    details=details,
                    candidate_name=candidate_name,
                    status=status or "success",
                )
            except Exception as e:
                logger.error(f"Failed to save activity log to database: {e}")
    except Exception as e:
        logger.error(f"Failed to log activity: {e}")


def get_recent_activities(session, limit: int = 10) -> List[Dict]:
    """
    Get the most recent activities from the session, in reverse chronological order.

    Args:
        session: Flask session object
        limit: Maximum number of activities to return (default 10)

    Returns:
        List of activity dicts, newest first
    """
    try:
        activities = list(session.get("activity_log", []))
        # Return in reverse chronological order (newest first)
        return list(reversed(activities))[:limit]
    except Exception as e:
        logger.error(f"Failed to retrieve activities: {e}")
        return []


def format_activity_icon(action: str) -> str:
    """Get Bootstrap icon class for an activity action type."""
    icons = {
        "upload": "bi-cloud-arrow-up-fill",
        "analyze": "bi-robot",
        "shortlist": "bi-check-circle-fill",
        "reject": "bi-x-circle-fill",
        "report": "bi-file-earmark-bar-graph",
        "delete": "bi-trash3-fill",
        "login": "bi-box-arrow-in-right",
        "save_job": "bi-save-fill",
        "clear_data": "bi-trash-fill",
    }
    return icons.get(action, "bi-info-circle-fill")


def format_activity_color(action: str) -> str:
    """Get color class for an activity action type."""
    colors = {
        "upload": "text-primary",
        "analyze": "text-info",
        "shortlist": "text-success",
        "reject": "text-danger",
        "report": "text-warning",
        "delete": "text-danger",
        "login": "text-success",
        "save_job": "text-primary",
        "clear_data": "text-danger",
    }
    return colors.get(action, "text-secondary")


def safe_get(d, key, default=None):
    """Safely get a value from a dict, returning default if key doesn't exist."""
    if d is None:
        return default
    return d.get(key, default)

