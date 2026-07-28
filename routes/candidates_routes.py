"""
candidates_routes.py
--------------------
Candidate Results page with ranking table and expandable
per-candidate ATS matching detail panels.
"""

import logging

from flask import Blueprint, render_template, session, jsonify

logger = logging.getLogger(__name__)

candidates_bp = Blueprint("candidates", __name__, url_prefix="/candidates")


def _require_login():
    if not session.get("logged_in"):
        return False
    return True


@candidates_bp.route("/")
def candidates():
    """Render the Candidate Results page."""
    if not _require_login():
        return render_template("login.html")

    all_candidates = session.get("candidates", [])
    analyzed = [c for c in all_candidates if c.get("scores")]
    # Pre-sort candidates by overall_score descending for template rendering
    analyzed.sort(key=lambda c: c.get("scores", {}).get("overall_score", 0), reverse=True)

    return render_template(
        "candidates.html",
        candidates=analyzed,
        total=len(analyzed),
        username=session.get("username", "User"),
    )


@candidates_bp.route("/api/detail/<candidate_id>")
def api_candidate_detail(candidate_id):
    """Return full candidate details including scores as JSON."""
    if not _require_login():
        return jsonify({"error": "Not logged in"}), 401

    candidates = session.get("candidates", [])
    for c in candidates:
        if c.get("id") == candidate_id:
            logger.info(f"Candidate detail viewed: {c.get('name', 'Unknown')} ({candidate_id})")
            return jsonify(c)

    logger.warning(f"Candidate detail not found: {candidate_id}")
    return jsonify({"error": "Candidate not found"}), 404


@candidates_bp.route("/api/ranking")
def api_ranking():
    """Return candidate ranking data as JSON for table rendering."""
    if not _require_login():
        return jsonify({"error": "Not logged in"}), 401

    candidates = session.get("candidates", [])
    analyzed = [c for c in candidates if c.get("scores")]
    ranked = sorted(analyzed, key=lambda c: c.get("scores", {}).get("overall_score", 0), reverse=True)

    result = []
    for c in ranked:
        scores = c.get("scores", {})
        result.append({
            "id": c.get("id", ""),
            "rank": c.get("rank", "-"),
            "name": c.get("name", "Unknown"),
            "email": c.get("email", "-"),
            "phone": c.get("phone", "-"),
            "skills": c.get("skills", []),
            "experience_years": c.get("experience_years", 0),
            "education": c.get("education", []),
            "role": c.get("role", "Not Found"),
            "department": c.get("department", "Not Found"),
            "location": scores.get("location", "Not Found"),
            "overall_score": scores.get("overall_score", 0),
            "status": scores.get("status", "Not analyzed"),
            "missing_skills": scores.get("missing_skills", []),
            "matched_skills": scores.get("matched_skills", []),
            "summary": scores.get("summary", ""),
            "skill_score": scores.get("skill_score", 0),
            "experience_score": scores.get("experience_score", 0),
            "education_score": scores.get("education_score", 0),
            "role_score": scores.get("role_score", 0),
            "department_score": scores.get("department_score", 0),
            "location_score": scores.get("location_score", 0),
            "projects_score": scores.get("projects_score", 0),
            "certifications_score": scores.get("certifications_score", 0),
            "verdict": scores.get("verdict", ""),
            "strengths": scores.get("strengths", [])[:8],
            "weaknesses": scores.get("weaknesses", [])[:8],
            "decision_reasons": scores.get("decision_reasons", []),
            "skill_breakdown": scores.get("skill_breakdown", []),
            "matched_requirements": scores.get("matching_report", {}).get("matched_requirements", []),
            "missing_requirements": scores.get("matching_report", {}).get("missing_requirements", []),
            "transparent_explanation": scores.get("transparent_explanation", ""),
            "score_breakdown": scores.get("score_breakdown", {}),
            "certifications": c.get("certifications", []),
            "projects": c.get("projects", []),
            "raw_text": c.get("raw_text", "")[:5000],
        })

    return jsonify(result)
