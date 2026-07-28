"""
main_routes.py
--------------
Main routes: Dashboard with KPIs, pipeline chart, rejection reasons,
and recent activity. All numbers computed live from session candidates.
"""

import logging
from flask import Blueprint, render_template, session, jsonify

from ai.ranking import summary_kpis, rejection_reasons_breakdown
from utils.helpers import get_recent_activities

logger = logging.getLogger(__name__)

main_bp = Blueprint("main", __name__)


def _require_login():
    """Check if user is logged in."""
    return session.get("logged_in", False)


@main_bp.route("/")
@main_bp.route("/dashboard")
def dashboard():
    """Render the main recruitment dashboard."""
    if not _require_login():
        return render_template("login.html")

    candidates = session.get("candidates", [])
    analyzed = [c for c in candidates if c.get("scores")]
    pending = [c for c in candidates if not c.get("scores")]
    job_description = session.get("job_description", {})

    kpis = summary_kpis(candidates)
    reasons = rejection_reasons_breakdown(candidates)

    # Recent analyzed (top 5 by rank)
    recent_analyzed = sorted(analyzed, key=lambda c: c.get("rank", 999))[:5]

    # Recent reports
    report_history = session.get("report_history", [])

    # Recent activities (from activity_log)
    recent_activities = get_recent_activities(session, limit=15)

    return render_template(
        "dashboard.html",
        total_candidates=kpis.get("total", 0),
        shortlisted=kpis.get("shortlisted", 0),
        rejected=kpis.get("rejected", 0),
        pending_count=len(pending),
        rejection_reasons=reasons,
        recent_analyzed=recent_analyzed,
        report_history=report_history[-5:],
        recent_activities=recent_activities,
        job_description=job_description,
        username=session.get("username", "User"),
    )


@main_bp.route("/api/kpis")
def api_kpis():
    """JSON endpoint for live KPI updates."""
    if not _require_login():
        return jsonify({"error": "Not logged in"}), 401

    try:
        candidates = session.get("candidates", [])
        analyzed = [c for c in candidates if c.get("scores")]
        pending = [c for c in candidates if not c.get("scores")]
        kpis = summary_kpis(candidates)
        reasons = rejection_reasons_breakdown(candidates)

        # Compute non-zero rejection reasons for chart
        non_zero_reasons = {k: v for k, v in reasons.items() if v > 0}

        # Recent activity
        recent_activities = get_recent_activities(session, limit=10)

        # Recent analyzed (top 5 by rank)
        recent_analyzed = sorted(analyzed, key=lambda c: c.get("rank", 999))[:5]

        # Serialize recent analyzed for JSON
        analyzed_data = []
        for c in recent_analyzed:
            scores = c.get("scores", {})
            analyzed_data.append({
                "rank": c.get("rank", "-"),
                "name": c.get("name", "Unknown"),
                "role": c.get("role", "N/A"),
                "score": scores.get("overall_score", 0),
                "status": scores.get("status", "-"),
            })

        return jsonify({
            "kpis": kpis,
            "pending_count": len(pending),
            "rejection_reasons": non_zero_reasons,
            "recent_analyzed": analyzed_data,
            "recent_activities": recent_activities,
        })
    except Exception as e:
        logger.error(f"Failed to fetch KPIs: {e}")
        return jsonify({"error": str(e)}), 500
