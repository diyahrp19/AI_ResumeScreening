"""
screening_routes.py
--------------------
Resume screening routes: upload resumes, enter job description,
analyze candidates. All AI logic from ai/ package reused unchanged.
All data is saved to the database with user_id so it persists
across sessions.
"""

import hashlib
import logging
import os
import time
import traceback
from datetime import datetime

from flask import (
    Blueprint, render_template, request, session,
    redirect, url_for, flash, jsonify, current_app,
)

from ai import parser, skill_extractor
from ai.matcher import match_candidate
from ai.ranking import rank_candidates
from ai.skill_extractor import _normalize_skill
from database import models
from utils.helpers import log_activity

# Get logger
logger = logging.getLogger(__name__)

screening_bp = Blueprint("screening", __name__, url_prefix="/screening")

EDUCATION_OPTIONS = [
    "High School", "Diploma", "Bachelor's Degree", "Master's Degree", "PhD", "Other",
]


def _require_login():
    if not session.get("logged_in"):
        return False
    return True


def _compute_file_hash(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


def _get_nlp():
    """Get NLP model from Flask app config."""
    from flask import current_app
    return current_app.config.get("NLP_MODEL")


def _get_user_id():
    """Get the current user's ID from session."""
    return session.get("user_id")


@screening_bp.route("/", methods=["GET", "POST"])
def screening():
    """Main screening page with upload, job description, and analysis."""
    if not _require_login():
        return redirect(url_for("auth.login"))

    candidates = session.get("candidates", [])
    job_description = session.get("job_description", {})

    if request.method == "POST":
        action = request.form.get("action", "")

        # ---- Upload Resumes ----
        if action == "upload":
            return _handle_upload()

        # ---- Save Job Description ----
        elif action == "save_job":
            return _handle_save_job()

        # ---- Analyze Candidates ----
        elif action == "analyze":
            return _handle_analyze()

    return render_template(
        "screening.html",
        candidates=candidates,
        job_description=job_description,
        education_options=EDUCATION_OPTIONS,
        username=session.get("username", "User"),
    )


def _handle_upload():
    """Process uploaded resume files and save to database."""
    uploaded_files = request.files.getlist("resumes")
    user_id = _get_user_id()

    if not uploaded_files or all(f.filename == "" for f in uploaded_files):
        flash("Please select at least one resume file to upload.", "error")
        return redirect(url_for("screening.screening"))

    nlp = _get_nlp()
    candidates = list(session.get("candidates", []))
    processed_ids = set(session.get("processed_file_ids", []))
    existing_hashes = {c.get("file_hash") for c in candidates if c.get("file_hash")}

    upload_dir = current_app.config["UPLOAD_FOLDER"]
    added = []
    failed = []
    skipped = []

    for uploaded_file in uploaded_files:
        if uploaded_file.filename == "":
            continue

        # Check extension
        ext = os.path.splitext(uploaded_file.filename)[1].lower()
        if ext not in (".pdf", ".docx"):
            failed.append((uploaded_file.filename, "Unsupported file type. Only PDF and DOCX are allowed."))
            continue

        file_bytes = uploaded_file.read()
        file_hash = _compute_file_hash(file_bytes)

        # Duplicate check within current session
        if file_hash in existing_hashes:
            skipped.append(uploaded_file.filename)
            continue

        # Add to processed set so we know it's been seen
        unique_id = f"{uploaded_file.filename}-{int(time.time()*1000)}"
        processed_ids.add(unique_id)

        # Save file to disk
        save_path = os.path.join(upload_dir, uploaded_file.filename)
        with open(save_path, "wb") as f:
            f.write(file_bytes)

        try:
            # Parse resume (reuses existing AI logic)
            text = parser.extract_text(save_path)
            sections = parser.segment_sections(text)

            name = parser.extract_name(text, nlp=nlp)
            email = parser.extract_email(text)
            phone = parser.extract_phone(text)
            links = parser.extract_links(text)
            experience_years = parser.extract_experience_years(text)
            skills = skill_extractor.extract_skills(text)
            education = skill_extractor.extract_education(text)
            certifications = skill_extractor.extract_certifications(
                sections.get("certifications", ""), text
            )
            projects = skill_extractor.extract_projects(sections.get("projects", ""))

            # Additional fields
            location = parser.extract_location(text)
            role = parser.extract_role(text)
            department = parser.extract_department(text)
            summary = parser.extract_summary(text)
            branch = parser.extract_branch_specialization(text)
            college = parser.extract_college_university(text)
            degree = parser.extract_degree_name(text)
            previous_role = parser.extract_previous_role(text)

            candidate = {
                "id": unique_id,
                "filename": uploaded_file.filename,
                "file_hash": file_hash,
                "name": name,
                "email": email or "Not found",
                "phone": phone or "Not found",
                "linkedin": links.get("linkedin"),
                "github": links.get("github"),
                "education": education,
                "experience_years": experience_years,
                "skills": skills,
                "certifications": certifications,
                "projects": projects,
                "raw_text": text,
                "location": location,
                "role": role,
                "department": department,
                "summary": summary,
                "branch": branch,
                "college": college,
                "degree": degree,
                "previous_role": previous_role,
                "upload_time": datetime.now().isoformat(timespec="seconds"),
                "scores": {},
            }

            candidates.append(candidate)
            existing_hashes.add(file_hash)
            added.append(uploaded_file.filename)
            # NOTE: Candidate is NOT saved to DB here yet.
            # It will be saved during analysis when scores are computed.
            # This prevents duplicate rows in the database.

        except parser.ResumeParseError as e:
            failed.append((uploaded_file.filename, str(e)))
        except Exception as e:
            failed.append((uploaded_file.filename, f"Unexpected error: {str(e)}"))

    # Save session state
    session["candidates"] = candidates
    session["processed_file_ids"] = list(processed_ids)
    session.modified = True

    # Log activities for successful uploads
    if added:
        for fname in added:
            log_activity(session, "upload", f"Uploaded resume: {fname}", fname, "success")
        flash(f"{len(added)} resume(s) uploaded successfully.", "success")
    if skipped:
        for fname in skipped:
            log_activity(session, "upload", f"Duplicate resume skipped: {fname}", fname, "warning")
        flash(f"{len(skipped)} file(s) were duplicates and were skipped.", "warning")
    if failed:
        for name, reason in failed:
            log_activity(session, "upload", f"Upload failed: {name} - {reason}", name, "error")
            flash(f"{name}: {reason}", "error")

    logger.info(f"Upload complete: {len(added)} added, {len(skipped)} skipped, {len(failed)} failed")
    return redirect(url_for("screening.screening"))


def _handle_save_job():
    """Save job description to session and database."""
    user_id = _get_user_id()
    title = request.form.get("title", "").strip()
    department = request.form.get("department", "").strip()
    location = request.form.get("location", "").strip()
    experience_years = request.form.get("experience_years", 2.0)
    education_choice = request.form.get("education_choice", "Bachelor's Degree")
    education_other = request.form.get("education_other", "").strip()
    skills_raw = request.form.get("skills", "").strip()

    if not title:
        flash("Job Title is required.", "error")
        return redirect(url_for("screening.screening"))

    if not skills_raw:
        flash("Required Skills are required.", "error")
        return redirect(url_for("screening.screening"))

    try:
        experience_years = float(experience_years)
    except (ValueError, TypeError):
        experience_years = 2.0

    skills = sorted({
        _normalize_skill(s.strip())
        for s in skills_raw.split(",")
        if s.strip()
    })

    final_education = education_other if education_choice == "Other" else education_choice

    job = {
        "title": title,
        "skills": skills,
        "experience_years": experience_years,
        "education": final_education,
        "education_choice": education_choice,
        "education_other": education_other,
        "department": department,
        "location": location,
    }

    session["job_description"] = job
    session.modified = True

    # Persist to database with user_id
    try:
        models.save_job_description(job, user_id=user_id)
        logger.info(f"Job description '{title}' saved to database for user {user_id}.")
    except Exception as e:
        logger.warning(f"Failed to persist job description to database: {e}")

    # Log activity
    log_activity(session, "save_job", f"Saved job description: {title}", "", "success")

    flash("Job description saved successfully.", "success")
    return redirect(url_for("screening.screening"))


def _handle_analyze():
    """Run AI analysis on all candidates against the job description.

    This function:
    1. Validates that a job description and candidates exist
    2. Runs match_candidate() on each candidate with proper error handling
    3. Saves results to database FIRST, then updates session
    4. Logs all activities
    5. Returns a detailed summary of results
    """
    job = session.get("job_description", {})
    candidates = list(session.get("candidates", []))
    user_id = _get_user_id()

    if not job:
        flash("Please save a Job Description before analyzing.", "error")
        return redirect(url_for("screening.screening"))

    if not candidates:
        flash("Please upload at least one resume before analyzing.", "error")
        return redirect(url_for("screening.screening"))

    # Validate job has required fields
    if not job.get("skills"):
        flash("Job description must have at least one required skill.", "error")
        return redirect(url_for("screening.screening"))

    logger.info(f"Starting analysis: {len(candidates)} candidate(s) against job '{job.get('title', 'Untitled')}'")

    analyzed_count = 0
    error_count = 0
    shortlist_count = 0
    reject_count = 0
    errors = []

    for cand in candidates:
        candidate_name = cand.get("name", "Unknown")
        try:
            # Run the ATS matching engine
            result = match_candidate(cand, job)

            # Validate that result contains all required score fields
            required_score_fields = [
                "skill_score", "experience_score", "education_score",
                "role_score", "department_score", "location_score",
                "projects_score", "certifications_score", "overall_score",
                "status", "verdict", "summary", "decision_reasons",
                "matched_skills", "missing_skills", "strengths", "weaknesses",
                "transparent_explanation", "matching_report", "mandatory_check",
            ]
            for field in required_score_fields:
                if field not in result:
                    logger.warning(f"Missing score field '{field}' for candidate {candidate_name}, adding default")
                    if field in ["matched_skills", "missing_skills", "strengths", "weaknesses", "decision_reasons"]:
                        result[field] = []
                    elif field in ["skill_score", "experience_score", "education_score", "role_score",
                                   "department_score", "location_score", "projects_score", "certifications_score",
                                   "overall_score"]:
                        result[field] = 0.0
                    elif field == "status":
                        result[field] = "Rejected"
                    elif field == "verdict":
                        result[field] = "Unable to evaluate"
                    elif field == "summary":
                        result[field] = "Analysis incomplete"
                    else:
                        result[field] = {}

            # Store results
            cand["scores"] = result
            cand["analyzed_at"] = datetime.now().isoformat(timespec="seconds")
            analyzed_count += 1

            # Track status counts
            if result.get("status") == "Shortlisted":
                shortlist_count += 1
                log_activity(session, "shortlist",
                    f"{candidate_name} shortlisted with {result.get('overall_score', 0)}% match",
                    candidate_name, "success")
            else:
                reject_count += 1
                # Get primary rejection reason
                reasons = result.get("decision_reasons", [])
                primary_reason = reasons[0] if reasons else "Requirements not met"
                log_activity(session, "reject",
                    f"{candidate_name} rejected: {primary_reason[:100]}",
                    candidate_name, "error")

            # Save to database with user_id (this will insert a new row)
            try:
                models.save_candidate(cand, user_id=user_id)
                logger.debug(f"Saved candidate '{candidate_name}' to database for user {user_id}.")
            except Exception as e:
                logger.error(f"Failed to save candidate '{candidate_name}' to database: {e}")
                errors.append(f"DB save failed for {candidate_name}: {str(e)}")

        except Exception as e:
            error_count += 1
            logger.error(f"Failed to analyze candidate '{candidate_name}': {e}")
            logger.debug(traceback.format_exc())
            errors.append(f"Analysis failed for {candidate_name}: {str(e)}")

            # Ensure candidate still has a scores dict even on failure
            if not cand.get("scores"):
                cand["scores"] = {
                    "skill_score": 0.0, "experience_score": 0.0, "education_score": 0.0,
                    "role_score": 0.0, "department_score": 0.0, "location_score": 0.0,
                    "projects_score": 0.0, "certifications_score": 0.0, "overall_score": 0.0,
                    "status": "Rejected", "verdict": "Analysis error",
                    "summary": f"An error occurred during analysis: {str(e)}",
                    "matched_skills": [], "missing_skills": [],
                    "strengths": [], "weaknesses": ["Analysis failed due to an error."],
                    "decision_reasons": [f"Analysis error: {str(e)}"],
                    "transparent_explanation": f"Analysis error: {str(e)}",
                    "matching_report": {"matched_requirements": [], "missing_requirements": [], "score_breakdown": {}},
                    "mandatory_check": {"all_satisfied": False, "results": {}, "failed_fields": ["analysis_error"], "rejection_reasons": [f"Analysis error: {str(e)}"]},
                }

    # Rank candidates (sorts by overall_score descending)
    if analyzed_count > 0:
        candidates = rank_candidates(candidates)
        logger.info(f"Ranked {analyzed_count} candidate(s) by match score.")

    # Persist back to session
    session["candidates"] = candidates
    session.modified = True

    # Log overall analysis activity
    log_activity(session, "analyze",
        f"Analyzed {analyzed_count} candidate(s) against '{job.get('title', 'Untitled')}': "
        f"{shortlist_count} shortlisted, {reject_count} rejected",
        "", "success" if error_count == 0 else "warning")

    # Flash appropriate message
    if error_count > 0:
        flash(
            f"Analysis completed: {analyzed_count} processed ({shortlist_count} shortlisted, "
            f"{reject_count} rejected), {error_count} failed. Check logs for details.",
            "warning"
        )
    elif analyzed_count > 0:
        flash(
            f"Analysis complete! {analyzed_count} candidate(s) analyzed: "
            f"{shortlist_count} shortlisted, {reject_count} rejected. "
            f"View detailed results in Candidate Results page.",
            "success"
        )

    return redirect(url_for("candidates.candidates"))


@screening_bp.route("/delete/<candidate_id>", methods=["POST"])
def delete_candidate(candidate_id):
    """Remove a candidate from the session."""
    if not _require_login():
        return jsonify({"error": "Not logged in"}), 401

    candidates = list(session.get("candidates", []))
    # Find the candidate name before removing
    candidate_name = "Unknown"
    for c in candidates:
        if c.get("id") == candidate_id:
            candidate_name = c.get("name", "Unknown")
            break

    candidates = [c for c in candidates if c.get("id") != candidate_id]
    session["candidates"] = candidates
    session.modified = True

    # Log activity
    log_activity(session, "delete", f"Removed candidate: {candidate_name}", candidate_name, "warning")
    logger.info(f"Candidate '{candidate_name}' removed from session.")

    return jsonify({"status": "success", "message": f"Candidate '{candidate_name}' removed"})


@screening_bp.route("/api/save_job", methods=["POST"])
def api_save_job():
    """AJAX endpoint: save job description and return JSON (no page reload)."""
    if not _require_login():
        return jsonify({"error": "Not logged in"}), 401

    user_id = _get_user_id()
    title = request.form.get("title", "").strip()
    department = request.form.get("department", "").strip()
    location = request.form.get("location", "").strip()
    experience_years = request.form.get("experience_years", 2.0)
    education_choice = request.form.get("education_choice", "Bachelor's Degree")
    education_other = request.form.get("education_other", "").strip()
    skills_raw = request.form.get("skills", "").strip()

    if not title:
        return jsonify({"error": "Job Title is required."}), 400
    if not skills_raw:
        return jsonify({"error": "Required Skills are required."}), 400

    try:
        experience_years = float(experience_years)
    except (ValueError, TypeError):
        experience_years = 2.0

    skills = sorted({
        _normalize_skill(s.strip())
        for s in skills_raw.split(",")
        if s.strip()
    })

    final_education = education_other if education_choice == "Other" else education_choice

    job = {
        "title": title,
        "skills": skills,
        "experience_years": experience_years,
        "education": final_education,
        "education_choice": education_choice,
        "education_other": education_other,
        "department": department,
        "location": location,
    }

    session["job_description"] = job
    session.modified = True

    try:
        models.save_job_description(job, user_id=user_id)
    except Exception as e:
        logger.warning(f"Failed to persist job description to database: {e}")

    log_activity(session, "save_job", f"Saved job description: {title}", "", "success")

    return jsonify({
        "success": True,
        "message": "Job description saved successfully.",
        "job": job,
    })


@screening_bp.route("/api/analyze", methods=["POST"])
def api_analyze():
    """AJAX endpoint: run analysis and return JSON results (no page reload)."""
    if not _require_login():
        return jsonify({"error": "Not logged in"}), 401

    job = session.get("job_description", {})
    candidates = list(session.get("candidates", []))
    user_id = _get_user_id()

    if not job:
        return jsonify({"error": "Please save a Job Description before analyzing."}), 400
    if not candidates:
        return jsonify({"error": "Please upload at least one resume before analyzing."}), 400
    if not job.get("skills"):
        return jsonify({"error": "Job description must have at least one required skill."}), 400

    logger.info(f"Starting AJAX analysis: {len(candidates)} candidate(s) against job '{job.get('title', 'Untitled')}'")

    analyzed_count = 0
    error_count = 0
    shortlist_count = 0
    reject_count = 0
    errors = []
    results = []

    for cand in candidates:
        candidate_name = cand.get("name", "Unknown")
        try:
            result = match_candidate(cand, job)

            # Ensure all required fields exist
            required_score_fields = [
                "skill_score", "experience_score", "education_score",
                "role_score", "department_score", "location_score",
                "projects_score", "certifications_score", "overall_score",
                "status", "verdict", "summary", "decision_reasons",
                "matched_skills", "missing_skills", "strengths", "weaknesses",
                "transparent_explanation", "matching_report", "mandatory_check",
            ]
            for field in required_score_fields:
                if field not in result:
                    if field in ["matched_skills", "missing_skills", "strengths", "weaknesses", "decision_reasons"]:
                        result[field] = []
                    elif field in ["skill_score", "experience_score", "education_score", "role_score",
                                   "department_score", "location_score", "projects_score", "certifications_score",
                                   "overall_score"]:
                        result[field] = 0.0
                    elif field == "status":
                        result[field] = "Rejected"
                    elif field == "verdict":
                        result[field] = "Unable to evaluate"
                    elif field == "summary":
                        result[field] = "Analysis incomplete"
                    else:
                        result[field] = {}

            cand["scores"] = result
            cand["analyzed_at"] = datetime.now().isoformat(timespec="seconds")
            analyzed_count += 1

            if result.get("status") == "Shortlisted":
                shortlist_count += 1
                log_activity(session, "shortlist",
                    f"{candidate_name} shortlisted with {result.get('overall_score', 0)}% match",
                    candidate_name, "success")
            else:
                reject_count += 1
                reasons = result.get("decision_reasons", [])
                primary_reason = reasons[0] if reasons else "Requirements not met"
                log_activity(session, "reject",
                    f"{candidate_name} rejected: {primary_reason[:100]}",
                    candidate_name, "error")

            results.append({
                "name": candidate_name,
                "status": result.get("status"),
                "overall_score": result.get("overall_score", 0),
                "filename": cand.get("filename", ""),
            })

            try:
                models.save_candidate(cand, user_id=user_id)
            except Exception as e:
                logger.error(f"Failed to save candidate '{candidate_name}' to database: {e}")
                errors.append(f"DB save failed for {candidate_name}: {str(e)}")

        except Exception as e:
            error_count += 1
            logger.error(f"Failed to analyze candidate '{candidate_name}': {e}")
            logger.debug(traceback.format_exc())
            errors.append(f"Analysis failed for {candidate_name}: {str(e)}")
            if not cand.get("scores"):
                cand["scores"] = {
                    "skill_score": 0.0, "experience_score": 0.0, "education_score": 0.0,
                    "role_score": 0.0, "department_score": 0.0, "location_score": 0.0,
                    "projects_score": 0.0, "certifications_score": 0.0, "overall_score": 0.0,
                    "status": "Rejected", "verdict": "Analysis error",
                    "summary": f"An error occurred during analysis: {str(e)}",
                    "matched_skills": [], "missing_skills": [],
                    "strengths": [], "weaknesses": ["Analysis failed due to an error."],
                    "decision_reasons": [f"Analysis error: {str(e)}"],
                    "transparent_explanation": f"Analysis error: {str(e)}",
                    "matching_report": {"matched_requirements": [], "missing_requirements": [], "score_breakdown": {}},
                    "mandatory_check": {"all_satisfied": False, "results": {}, "failed_fields": ["analysis_error"], "rejection_reasons": [f"Analysis error: {str(e)}"]},
                }

    if analyzed_count > 0:
        candidates = rank_candidates(candidates)

    session["candidates"] = candidates
    session.modified = True

    log_activity(session, "analyze",
        f"Analyzed {analyzed_count} candidate(s) against '{job.get('title', 'Untitled')}': "
        f"{shortlist_count} shortlisted, {reject_count} rejected",
        "", "success" if error_count == 0 else "warning")

    return jsonify({
        "success": True,
        "analyzed_count": analyzed_count,
        "shortlist_count": shortlist_count,
        "reject_count": reject_count,
        "error_count": error_count,
        "errors": errors,
        "results": results,
        "message": (
            f"Analysis complete! {analyzed_count} candidate(s) analyzed: "
            f"{shortlist_count} shortlisted, {reject_count} rejected."
        ),
    })


@screening_bp.route("/api/job_description", methods=["GET"])
def api_job_description():
    """Return current job description as JSON."""
    if not _require_login():
        return jsonify({}), 401
    return jsonify(session.get("job_description", {}))

