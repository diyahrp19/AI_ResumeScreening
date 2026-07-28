"""
matcher.py
----------
Comprehensive ATS (Applicant Tracking System) matching engine.
Compares every field from the candidate's resume against the job
description using strict mandatory/optional rules and produces a
transparent, auditable matching report.

Score composition (weights sum to 100%):
    - Skills                   : 40%
    - Experience                : 20%
    - Education                 : 10%
    - Role                      : 10%
    - Department                : 5%
    - Location                  : 10%
    - Projects                  : 3%
    - Certifications            : 2%

Mandatory fields (must be satisfied or candidate is rejected):
    - Skills (at least 50% match)
    - Experience (>= required)
    - Education (rank >= required)
    - Location (must match)
    - Role (must match)
    - Department (must match)

Decision Engine (Rule-Based):
    IF Location Mismatch    -> Reject
    IF Experience < Required -> Reject
    IF Required Degree Missing -> Reject
    IF Required Skills Missing (< 50%) -> Reject
"""

from typing import Dict, List, Tuple
from ai.knowledge_base import EDUCATION_RANK, MANDATORY_FIELDS, OPTIONAL_FIELDS, get_parent_department, departments_match
from ai.skill_extractor import highest_education_rank

# Configurable thresholds
CLASSIFICATION_THRESHOLDS = {
    "shortlist": 60.0,  # >= 60%: Shortlisted
    "min_skill_match": 0.5,  # Minimum 50% skills required
    "min_experience_ratio": 1.0,  # Must meet 100% of required experience
}

# ATS Weights
WEIGHTS = {
    "skill": 0.40,
    "experience": 0.20,
    "education": 0.10,
    "role": 0.10,
    "department": 0.05,
    "location": 0.10,
    "projects": 0.03,
    "certifications": 0.02,
}


def _check_mandatory_requirements(candidate: dict, job: dict) -> Dict:
    """
    Check all mandatory requirements. Returns a dict with:
    - all_satisfied: bool
    - results: dict of field -> {"matched": bool, "detail": str}
    - failed_fields: list of field names that failed
    - rejection_reasons: list of human-readable rejection reasons
    """
    results = {}
    failed = []
    rejection_reasons = []
    
    # 1. Skills check (at least 50% match)
    required_skills = set(job.get("skills", []))
    candidate_skills = set(candidate.get("skills", []))
    if required_skills:
        matched_skills = required_skills & candidate_skills
        missing_skills = required_skills - candidate_skills
        skill_ratio = len(matched_skills) / len(required_skills)
        skill_matched = skill_ratio >= CLASSIFICATION_THRESHOLDS["min_skill_match"]
        results["skills"] = {
            "matched": skill_matched,
            "detail": f"{len(matched_skills)}/{len(required_skills)} skills matched",
            "matched_items": sorted(matched_skills),
            "missing_items": sorted(missing_skills),
            "ratio": skill_ratio,
        }
        if not skill_matched:
            failed.append("skills")
            rejection_reasons.append(f"Insufficient skills match ({len(matched_skills)}/{len(required_skills)} required skills matched). Missing: {', '.join(sorted(missing_skills)[:5])}")
    else:
        results["skills"] = {"matched": True, "detail": "No skills required", "matched_items": [], "missing_items": [], "ratio": 1.0}
    
    # 2. Experience check (strict: must meet or exceed required)
    required_exp = float(job.get("experience_years", 0) or 0)
    candidate_exp = float(candidate.get("experience_years", 0) or 0)
    if required_exp > 0:
        exp_match = candidate_exp >= required_exp
        results["experience"] = {
            "matched": exp_match,
            "detail": f"Required: {required_exp} yrs, Candidate: {candidate_exp} yrs",
            "required": required_exp,
            "candidate": candidate_exp,
        }
        if not exp_match:
            failed.append("experience")
            rejection_reasons.append(f"Insufficient experience ({candidate_exp} yrs < required {required_exp} yrs).")
    else:
        results["experience"] = {"matched": True, "detail": "No experience required", "required": 0, "candidate": candidate_exp}
    
    # 3. Education check
    required_edu = (job.get("education") or "").lower().strip()
    if required_edu:
        required_rank = 0
        for key, rank in EDUCATION_RANK.items():
            if key in required_edu:
                required_rank = max(required_rank, rank)
        candidate_edu_list = candidate.get("education", [])
        candidate_rank = highest_education_rank(candidate_edu_list)
        edu_match = candidate_rank >= required_rank
        results["education"] = {
            "matched": edu_match,
            "detail": f"Required: {required_edu.title()}, Candidate: {', '.join(candidate_edu_list) or 'Not Found'}",
            "required": required_edu,
            "candidate": ", ".join(candidate_edu_list) or "Not Found",
        }
        if not edu_match:
            failed.append("education")
            if candidate_rank == 0:
                rejection_reasons.append(f"Required education ({required_edu.title()}) not found on resume.")
            else:
                rejection_reasons.append(f"Required education ({required_edu.title()}) does not match candidate's education level.")
    else:
        results["education"] = {"matched": True, "detail": "No education required", "required": "", "candidate": ""}
    
    # 4. Location check (strict match)
    job_location = (job.get("location") or "").strip().lower()
    candidate_location = (candidate.get("location") or "").strip().lower()
    if job_location:
        loc_match = (job_location in candidate_location or candidate_location in job_location) and candidate_location != "not found"
        results["location"] = {
            "matched": loc_match,
            "detail": f"Required: {job.get('location', '')}, Candidate: {candidate.get('location', 'Not Found')}",
            "required": job.get("location", ""),
            "candidate": candidate.get("location", "Not Found"),
        }
        if not loc_match:
            failed.append("location")
            rejection_reasons.append(f"Required location ({job.get('location', '')}) does not match candidate location ({candidate.get('location', 'Not Found')}).")
    else:
        results["location"] = {"matched": True, "detail": "No location required", "required": "", "candidate": candidate.get("location", "Not Found")}
    
    # 5. Role check
    job_role = (job.get("role") or job.get("title") or "").strip().lower()
    candidate_role = (candidate.get("role") or "").strip().lower()
    if job_role:
        # Role matching: check if required role appears in candidate role or vice versa
        role_match = job_role in candidate_role or candidate_role in job_role
        # Don't auto-match "not found" candidates
        if candidate_role == "not found":
            role_match = False
        results["role"] = {
            "matched": role_match,
            "detail": f"Required: {job.get('role', job.get('title', ''))}, Candidate: {candidate.get('role', 'Not Found')}",
            "required": job.get("role", job.get("title", "")),
            "candidate": candidate.get("role", "Not Found"),
        }
        if not role_match:
            failed.append("role")
            rejection_reasons.append(f"Required role ({job.get('role', job.get('title', ''))}) does not match candidate role ({candidate.get('role', 'Not Found')}).")
    else:
        results["role"] = {"matched": True, "detail": "No role specified", "required": "", "candidate": candidate.get("role", "Not Found")}
    
    # 6. Department check (using smart hierarchy matching)
    job_dept = (job.get("department") or "").strip()
    candidate_dept = (candidate.get("department") or "").strip()
    if job_dept:
        # Use smart department hierarchy matching
        dept_match = departments_match(job_dept, candidate_dept)
        results["department"] = {
            "matched": dept_match,
            "detail": f"Required: {job.get('department', '')}, Candidate: {candidate.get('department', 'Not Found')}",
            "required": job.get("department", ""),
            "candidate": candidate.get("department", "Not Found"),
        }
        if not dept_match:
            failed.append("department")
            # Provide a more helpful rejection reason
            job_parent = get_parent_department(job_dept)
            candidate_parent = get_parent_department(candidate_dept)
            rejection_reasons.append(
                f"Department mismatch: Required '{job.get('department', '')}' ({job_parent}), "
                f"candidate is from '{candidate.get('department', 'Not Found')}' "
                f"({candidate_parent if candidate_parent != 'not found' else 'Unknown'})."
            )
    else:
        results["department"] = {"matched": True, "detail": "No department specified", "required": "", "candidate": candidate.get("department", "Not Found")}
    
    return {
        "all_satisfied": len(failed) == 0,
        "results": results,
        "failed_fields": failed,
        "rejection_reasons": rejection_reasons,
    }


def _check_optional_requirements(candidate: dict, job: dict) -> Dict:
    """Check optional requirements (certifications, projects)."""
    results = {}
    
    # Certifications
    job_certs = job.get("certifications", [])
    candidate_certs = candidate.get("certifications", [])
    if job_certs:
        matched_certs = [c for c in candidate_certs if any(jc.lower() in c.lower() for jc in job_certs)]
        results["certifications"] = {
            "matched": len(matched_certs) > 0,
            "detail": f"{len(matched_certs)}/{len(job_certs)} certifications matched",
            "matched_items": matched_certs,
            "count": len(candidate_certs),
        }
    else:
        results["certifications"] = {"matched": True, "detail": "No certifications required", "count": len(candidate.get("certifications", []))}
    
    # Projects
    job_skills = set(job.get("skills", []))
    candidate_projects = candidate.get("projects", [])
    if candidate_projects:
        relevant_projects = [p for p in candidate_projects if any(s in p.lower() for s in job_skills)]
        results["projects"] = {
            "matched": len(relevant_projects) > 0,
            "detail": f"{len(relevant_projects)} relevant projects found",
            "count": len(candidate_projects),
            "relevant_count": len(relevant_projects),
        }
    else:
        results["projects"] = {"matched": False, "detail": "No projects found", "count": 0, "relevant_count": 0}
    
    return results


def _calculate_scores(candidate: dict, job: dict, mandatory: Dict, optional: Dict) -> Dict:
    """Calculate weighted scores for each category."""
    
    # Skills score (0-100)
    required_skills = set(job.get("skills", []))
    candidate_skills = set(candidate.get("skills", []))
    if required_skills:
        skill_score = round((len(required_skills & candidate_skills) / len(required_skills)) * 100, 1)
    else:
        skill_score = 100.0 if candidate_skills else 0.0
    
    # Experience score (0-100)
    required_exp = float(job.get("experience_years", 0) or 0)
    candidate_exp = float(candidate.get("experience_years", 0) or 0)
    if required_exp <= 0:
        exp_score = 100.0
    elif candidate_exp >= required_exp:
        exp_score = 100.0
    else:
        # Penalize significantly for insufficient experience
        exp_score = round((candidate_exp / required_exp) * 60, 1)  # Max 60% if below requirement
    
    # Education score (0-100)
    required_edu = (job.get("education") or "").lower().strip()
    if required_edu:
        required_rank = 0
        for key, rank in EDUCATION_RANK.items():
            if key in required_edu:
                required_rank = max(required_rank, rank)
        candidate_rank = highest_education_rank(candidate.get("education", []))
        if candidate_rank >= required_rank:
            edu_score = 100.0
        elif candidate_rank == 0:
            edu_score = 10.0  # Very low if no education detected
        else:
            edu_score = round((candidate_rank / required_rank) * 50, 1)  # Max 50% if below
    else:
        edu_score = 100.0
    
    # Role score (0 or 100)
    role_score = 100.0 if mandatory["results"].get("role", {}).get("matched", True) else 0.0
    
    # Department score (0 or 100)
    dept_score = 100.0 if mandatory["results"].get("department", {}).get("matched", True) else 0.0
    
    # Location score (0 or 100)
    loc_score = 100.0 if mandatory["results"].get("location", {}).get("matched", True) else 0.0
    
    # Projects score (0-100)
    projects = candidate.get("projects", [])
    if projects:
        proj_score = min(100.0, len(projects) * 20.0)
    else:
        proj_score = 0.0
    
    # Certifications score (0-100)
    certs = candidate.get("certifications", [])
    if certs:
        cert_score = min(100.0, len(certs) * 25.0)
    else:
        cert_score = 0.0
    
    return {
        "skill": skill_score,
        "experience": exp_score,
        "education": edu_score,
        "role": role_score,
        "department": dept_score,
        "location": loc_score,
        "projects": proj_score,
        "certifications": cert_score,
    }


def _build_matching_report(candidate: dict, job: dict, mandatory: Dict, optional: Dict, scores: Dict, overall_score: float, status: str, decision_reason: str = "") -> Dict:
    """Build the detailed matching report for display with matched/missing requirements."""
    
    report = {
        "field_comparison": {},
        "matched_requirements": [],
        "missing_requirements": [],
        "score_breakdown": {},
    }
    
    # Build field comparison
    for field in ["skills", "experience", "education", "location", "role", "department"]:
        field_result = mandatory["results"].get(field, {})
        report["field_comparison"][field] = field_result
    
    # Add projects and certifications
    report["field_comparison"]["projects"] = optional.get("projects", {})
    report["field_comparison"]["certifications"] = optional.get("certifications", {})
    
    # Build matched/missing lists with clean display format
    for field, result in mandatory["results"].items():
        if result.get("matched", False):
            if field == "skills":
                for s in result.get("matched_items", []):
                    report["matched_requirements"].append(f"✔ {s}")
            elif field == "experience":
                report["matched_requirements"].append(f"✔ Experience: {result.get('detail', 'Matched')}")
            elif field == "education":
                report["matched_requirements"].append(f"✔ {result.get('candidate', 'Degree')}")
            elif field == "location":
                report["matched_requirements"].append(f"✔ Location: {result.get('candidate', 'Matched')}")
            elif field == "role":
                report["matched_requirements"].append(f"✔ Role: {result.get('candidate', 'Matched')}")
            elif field == "department":
                report["matched_requirements"].append(f"✔ Department: {result.get('candidate', 'Matched')}")
            else:
                report["matched_requirements"].append(f"✔ {field.title()}: {result.get('detail', 'Matched')}")
        else:
            if field == "skills":
                for s in result.get("missing_items", []):
                    report["missing_requirements"].append(f"✖ {s}")
            elif field == "experience":
                report["missing_requirements"].append(f"✖ Experience: {result.get('detail', 'Not matched')}")
            elif field == "education":
                report["missing_requirements"].append(f"✖ {result.get('detail', 'Not matched')}")
            elif field == "location":
                report["missing_requirements"].append(f"✖ Location: {result.get('candidate', 'Not Found')}")
            elif field == "role":
                report["missing_requirements"].append(f"✖ Role: {result.get('candidate', 'Not Found')}")
            elif field == "department":
                report["missing_requirements"].append(f"✖ Department: {result.get('candidate', 'Not Found')}")
            else:
                report["missing_requirements"].append(f"✖ {field.title()}: {result.get('detail', 'Not matched')}")
    
    # Add optional field results
    for field in ["projects", "certifications"]:
        result = optional.get(field, {})
        if result.get("matched", False):
            if field == "projects":
                report["matched_requirements"].append(f"✔ {result.get('relevant_count', 0)} Relevant Projects")
            elif field == "certifications":
                cert_items = result.get("matched_items", [])
                if cert_items:
                    for cert in cert_items[:3]:
                        report["matched_requirements"].append(f"✔ {cert}")
                else:
                    report["matched_requirements"].append(f"✔ {result.get('detail', 'Found')}")
        else:
            if field == "projects":
                report["missing_requirements"].append("✖ No Relevant Projects")
            elif field == "certifications":
                report["missing_requirements"].append("✖ No Certifications")
    
    # Build score breakdown
    for field, weight in WEIGHTS.items():
        score = scores.get(field, 0)
        weighted = round(score * weight, 1)
        report["score_breakdown"][field] = {
            "score": score,
            "weight": weight * 100,
            "weighted": weighted,
            "max_weighted": round(weight * 100, 1),
        }
    
    report["overall_score"] = overall_score
    report["status"] = status
    if decision_reason:
        report["decision_reason"] = decision_reason
    
    return report


def match_candidate(candidate: dict, job: dict) -> Dict:
    """
    Main entry point: comprehensive ATS matching.
    Returns a dict with all scores, comparisons, and the final decision.
    """
    try:
        # Step 1: Check mandatory requirements
        mandatory = _check_mandatory_requirements(candidate, job)
        
        # Step 2: Check optional requirements
        optional = _check_optional_requirements(candidate, job)
        
        # Step 3: Calculate scores
        scores = _calculate_scores(candidate, job, mandatory, optional)
        
        # Step 4: Calculate overall weighted score
        overall_score = sum(scores[f] * WEIGHTS[f] for f in WEIGHTS)
        overall_score = max(0.0, min(100.0, round(overall_score, 1)))
        
        # Step 5: Decision Engine (Rule-Based)
        # Rules are evaluated in priority order:
        # Rule 1: IF Location Mismatch THEN Reject
        # Rule 2: IF Experience < Required THEN Reject
        # Rule 3: IF Required Degree Missing THEN Reject
        # Rule 4: IF Required Skills Missing (< 50%) THEN Reject
        
        decision_reasons = []
        is_rejected = False
        
        # Check each mandatory field failure and build rejection reasons
        if not mandatory["all_satisfied"]:
            is_rejected = True
            rejection_reasons = mandatory.get("rejection_reasons", [])
            decision_reasons = rejection_reasons
            status = "Rejected"
            # Build a clear rejection reason
            if len(rejection_reasons) == 1:
                reason = rejection_reasons[0]
            else:
                reason = "Multiple requirements not met: " + "; ".join(rejection_reasons[:3])
            verdict = f"Weak match - {reason}"
        elif overall_score >= CLASSIFICATION_THRESHOLDS["shortlist"]:
            status = "Shortlisted"
            # Build shortlist reason
            matched_fields = [f for f in mandatory["failed_fields"] if f not in mandatory["failed_fields"]]
            decision_reasons.append("All mandatory requirements satisfied.")
            verdict = f"Strong match - recommended for interview (Score: {overall_score}%)"
        else:
            status = "Rejected"
            decision_reasons.append(f"Overall score ({overall_score}%) below shortlist threshold ({CLASSIFICATION_THRESHOLDS['shortlist']}%).")
            verdict = f"Weak match - does not currently meet the role's requirements (Score: {overall_score}%)"
        
        # Step 6: Build matching report
        report = _build_matching_report(candidate, job, mandatory, optional, scores, overall_score, status, "; ".join(decision_reasons) if decision_reasons else "")
        
        # Step 7: Build transparent explanation
        explanation_parts = []
        explanation_parts.append("## Detailed ATS Matching Report")
        explanation_parts.append(f"**Candidate:** {candidate.get('name', 'Unknown')}")
        explanation_parts.append("")
        
        # Skills section
        skill_result = mandatory["results"].get("skills", {})
        explanation_parts.append("### Skills")
        if skill_result.get("matched_items"):
            for s in skill_result["matched_items"]:
                explanation_parts.append(f"✔ {s}")
        if skill_result.get("missing_items"):
            for s in skill_result["missing_items"]:
                explanation_parts.append(f"✖ {s}")
        if not skill_result.get("matched_items") and not skill_result.get("missing_items"):
            explanation_parts.append("*No skills comparison available*")
        explanation_parts.append("")
        
        # Experience section
        exp_result = mandatory["results"].get("experience", {})
        explanation_parts.append("### Experience")
        explanation_parts.append(f"Required: {exp_result.get('required', 0)} Years")
        explanation_parts.append(f"Candidate: {exp_result.get('candidate', 0)} Years")
        if exp_result.get("matched", False):
            explanation_parts.append("✔ Matched")
        else:
            explanation_parts.append("❌ Not Matched")
        explanation_parts.append("")
        
        # Education section
        edu_result = mandatory["results"].get("education", {})
        explanation_parts.append("### Education")
        explanation_parts.append(f"Required: {edu_result.get('required', 'N/A')}")
        explanation_parts.append(f"Candidate: {edu_result.get('candidate', 'Not Found')}")
        if edu_result.get("matched", False):
            explanation_parts.append("✔ Matched")
        else:
            explanation_parts.append("❌ Not Matched")
        explanation_parts.append("")
        
        # Department section
        dept_result = mandatory["results"].get("department", {})
        explanation_parts.append("### Department")
        explanation_parts.append(f"Required: {dept_result.get('required', 'N/A')}")
        explanation_parts.append(f"Candidate: {dept_result.get('candidate', 'Not Found')}")
        if dept_result.get("matched", False):
            explanation_parts.append("✔ Matched")
        else:
            explanation_parts.append("❌ Not Matched")
        explanation_parts.append("")
        
        # Role section
        role_result = mandatory["results"].get("role", {})
        explanation_parts.append("### Role")
        explanation_parts.append(f"Required: {role_result.get('required', 'N/A')}")
        explanation_parts.append(f"Candidate: {role_result.get('candidate', 'Not Found')}")
        if role_result.get("matched", False):
            explanation_parts.append("✔ Matched")
        else:
            explanation_parts.append("❌ Not Matched")
        explanation_parts.append("")
        
        # Location section
        loc_result = mandatory["results"].get("location", {})
        explanation_parts.append("### Location")
        explanation_parts.append(f"Required: {loc_result.get('required', 'N/A')}")
        explanation_parts.append(f"Candidate: {loc_result.get('candidate', 'Not Found')}")
        if loc_result.get("matched", False):
            explanation_parts.append("✔ Matched")
        else:
            explanation_parts.append("❌ Not Matched")
        explanation_parts.append("")
        
        # Projects section
        proj_result = optional.get("projects", {})
        explanation_parts.append("### Projects")
        if proj_result.get("count", 0) > 0:
            explanation_parts.append(f"✔ {proj_result.get('count', 0)} Projects Found")
            if proj_result.get("relevant_count", 0) > 0:
                explanation_parts.append(f"✔ {proj_result.get('relevant_count', 0)} Relevant to Required Skills")
        else:
            explanation_parts.append("✖ No Projects Found")
        explanation_parts.append("")
        
        # Certifications section
        cert_result = optional.get("certifications", {})
        explanation_parts.append("### Certifications")
        if cert_result.get("count", 0) > 0:
            explanation_parts.append(f"✔ {cert_result.get('count', 0)} Certifications Found")
        else:
            explanation_parts.append("✖ No Certifications Found")
        explanation_parts.append("")
        
        # Overall Result
        explanation_parts.append("---")
        explanation_parts.append(f"### Overall Result: {status}")
        explanation_parts.append(f"**{verdict}**")
        if decision_reasons:
            explanation_parts.append("")
            explanation_parts.append("**Decision Reasons:**")
            for reason in decision_reasons:
                explanation_parts.append(f"- {reason}")
        explanation_parts.append("")
        
        # Score breakdown
        explanation_parts.append("### Score Breakdown")
        for field, data in report["score_breakdown"].items():
            explanation_parts.append(f"{field.title()}: {data['score']:.0f}% × {data['weight']:.0f}% = {data['weighted']:.1f}/{data['max_weighted']:.0f}")
        explanation_parts.append(f"**Final Score: {overall_score}%**")
        
        transparent_explanation = "\n".join(explanation_parts)
        
        # Build skill breakdown for UI compatibility
        skill_breakdown = []
        for s in skill_result.get("matched_items", []):
            skill_breakdown.append({"skill": s, "found": True, "points": 0.0})
        for s in skill_result.get("missing_items", []):
            skill_breakdown.append({"skill": s, "found": False, "points": 0.0})
        
        # Add location to skill breakdown
        loc_matched = mandatory["results"].get("location", {}).get("matched", False)
        loc_candidate = mandatory["results"].get("location", {}).get("candidate", "Not Found")
        skill_breakdown.append({
            "skill": f"📍 Location: {loc_candidate}",
            "found": loc_matched,
            "points": 10.0 if loc_matched else 0.0,
        })
        
        # Add role to skill breakdown
        role_matched = mandatory["results"].get("role", {}).get("matched", False)
        role_candidate = mandatory["results"].get("role", {}).get("candidate", "Not Found")
        skill_breakdown.append({
            "skill": f"💼 Role: {role_candidate}",
            "found": role_matched,
            "points": 10.0 if role_matched else 0.0,
        })
        
        # Add department to skill breakdown
        dept_matched = mandatory["results"].get("department", {}).get("matched", False)
        dept_candidate = mandatory["results"].get("department", {}).get("candidate", "Not Found")
        skill_breakdown.append({
            "skill": f"🏢 Department: {dept_candidate}",
            "found": dept_matched,
            "points": 5.0 if dept_matched else 0.0,
        })
        
        return {
            "skill_score": scores["skill"],
            "experience_score": scores["experience"],
            "education_score": scores["education"],
            "role_score": scores["role"],
            "department_score": scores["department"],
            "location_score": scores["location"],
            "projects_score": scores["projects"],
            "certifications_score": scores["certifications"],
            "projects_certifications_score": scores["projects"] * 0.6 + scores["certifications"] * 0.4,
            "projects_certifications_explanation": f"Projects: {optional.get('projects', {}).get('count', 0)} found, Certifications: {optional.get('certifications', {}).get('count', 0)} found",
            "location_match": mandatory["results"].get("location", {}).get("matched", False),
            "location": mandatory["results"].get("location", {}).get("candidate", "Not Found"),
            "location_explanation": mandatory["results"].get("location", {}).get("detail", ""),
            "skill_breakdown": skill_breakdown,
            "overall_score": overall_score,
            "score_breakdown": report["score_breakdown"],
            "transparent_explanation": transparent_explanation,
            "matching_report": report,
            "mandatory_check": mandatory,
            "optional_check": optional,
            "missing_skills": skill_result.get("missing_items", []),
            "matched_skills": skill_result.get("matched_items", []),
            "status": status,
            "verdict": verdict,
            "summary": f"Overall score: {overall_score}%. {verdict}",
            "strengths": report["matched_requirements"][:10],
            "weaknesses": report["missing_requirements"][:10],
            "decision_reasons": decision_reasons,
            "rule_breakdown": [],
        }
    except Exception as e:
        # Safe fallback
        import traceback
        return {
            "skill_score": 0.0,
            "experience_score": 0.0,
            "education_score": 0.0,
            "role_score": 0.0,
            "department_score": 0.0,
            "location_score": 0.0,
            "projects_score": 0.0,
            "certifications_score": 0.0,
            "projects_certifications_score": 0.0,
            "projects_certifications_explanation": "Error during evaluation.",
            "location_match": False,
            "location": "Not Found",
            "location_explanation": "Error during evaluation.",
            "skill_breakdown": [],
            "overall_score": 0.0,
            "missing_skills": [],
            "matched_skills": [],
            "status": "Rejected",
            "verdict": "Unable to evaluate candidate.",
            "summary": "An error occurred during analysis.",
            "strengths": [],
            "weaknesses": ["Analysis failed due to an error."],
            "decision_reasons": [f"Analysis error: {str(e)}"],
            "rule_breakdown": [],
            "transparent_explanation": f"An error occurred during analysis: {str(e)}",
            "matching_report": {},
            "mandatory_check": {"all_satisfied": False, "results": {}, "failed_fields": ["analysis_error"], "rejection_reasons": [f"Analysis error: {str(e)}"]},
            "optional_check": {},
        }