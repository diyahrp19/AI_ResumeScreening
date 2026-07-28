"""
ranking.py
----------
Ranks a list of already-scored candidates and provides small analytics
helper aggregations used by the Dashboard and Analytics pages.
"""

from typing import List, Dict
import pandas as pd


STATUS_ICONS = {"Shortlisted": "✅", "Rejected": "❌"}


def rank_candidates(candidates: List[dict]) -> List[dict]:
    """Sort candidates by overall_score descending and assign a rank."""
    sorted_candidates = sorted(
        candidates, key=lambda c: c.get("scores", {}).get("overall_score", 0), reverse=True
    )
    for i, cand in enumerate(sorted_candidates, start=1):
        cand["rank"] = i
    return sorted_candidates


def candidates_to_dataframe(candidates: List[dict]) -> pd.DataFrame:
    """Flatten candidate records into a DataFrame for tables/exports."""
    rows = []
    for c in candidates:
        scores = c.get("scores", {})
        if not scores:
            continue
        status = scores.get("status", "-")
        icon = STATUS_ICONS.get(status, "")
        
        # Safely handle education field
        education = c.get("education", [])
        education_text = ", ".join(education) if education else "-"
        
        # Safely handle missing skills
        missing_skills = scores.get("missing_skills", [])
        missing_text = ", ".join(missing_skills) if missing_skills else "None"
        
        rows.append({
            "Rank": c.get("rank", "-"),
            "Candidate": c.get("name", "Unknown"),
            "Email": c.get("email", "-"),
            "Phone": c.get("phone", "-"),
            "Experience (yrs)": c.get("experience_years", 0),
            "Education": education_text,
            "Branch": c.get("branch", "Not Found"),
            "College": c.get("college", "Not Found"),
            "Degree": c.get("degree", "Not Found"),
            "Role": c.get("role", "Not Found"),
            "Department": c.get("department", "Not Found"),
            "Match Score": scores.get("overall_score", 0),
            "Skill Match": scores.get("skill_score", 0),
            "Experience Match": scores.get("experience_score", 0),
            "Education Match": scores.get("education_score", 0),
            "Projects & Certs Match": scores.get("projects_certifications_score", 0),
            "Location": scores.get("location", "Not Found"),
            "Location Match": "✔" if scores.get("location_match", False) else "✖",
            "Status": status,
            "Status Display": f"{icon} {status}".strip(),
            "Recommendation": scores.get("verdict", "-"),
            "Missing Skills": missing_text,
            "Uploaded": c.get("upload_time", "-"),
        })
    return pd.DataFrame(rows)


def summary_kpis(candidates: List[dict]) -> Dict:
    """
    Total/Shortlisted/Rejected/Avg-Score, computed live from whatever
    candidates currently exist in the pool - never placeholder or
    random values. Only Shortlisted/Rejected are tracked (no
    intermediate "Review" bucket).
    Uses safe .get() access to prevent crashes on missing/incomplete data.
    """
    # Only count unique candidates by file_hash to avoid duplicates
    seen_hashes = set()
    unique_candidates = []
    for c in candidates:
        h = c.get("file_hash", "")
        if h and h in seen_hashes:
            continue
        if h:
            seen_hashes.add(h)
        unique_candidates.append(c)

    total = len(unique_candidates)
    shortlisted = sum(1 for c in unique_candidates if c.get("scores", {}).get("status") == "Shortlisted")
    rejected = sum(1 for c in unique_candidates if c.get("scores", {}).get("status") == "Rejected")
    analyzed = sum(1 for c in unique_candidates if c.get("scores"))
    avg_score = (
        round(sum(c.get("scores", {}).get("overall_score", 0) for c in unique_candidates) / analyzed, 1)
        if analyzed else 0.0
    )
    return {
        "total": total,
        "shortlisted": shortlisted,
        "rejected": rejected,
        "avg_score": avg_score,
    }


def top_skills(candidates: List[dict], top_n: int = 10) -> Dict[str, int]:
    freq: Dict[str, int] = {}
    for c in candidates:
        for skill in c.get("skills", []):
            freq[skill] = freq.get(skill, 0) + 1
    return dict(sorted(freq.items(), key=lambda x: x[1], reverse=True)[:top_n])


def rejection_reasons_breakdown(candidates: List[dict]) -> Dict[str, int]:
    """
    Aggregate rejection reasons across all rejected candidates.
    Returns a dict like:
      {
        "Skills Missing": 3,
        "Experience Mismatch": 2,
        "Degree Mismatch": 1,
        "Location Mismatch": 0,
        "Role Mismatch": 1,
        "Department Mismatch": 0,
      }
    
    Reasons are extracted from the candidate's scores -> decision_reasons
    or from the mandatory_check -> rejection_reasons in the matching report.
    """
    reasons = {
        "Skills Missing": 0,
        "Experience Mismatch": 0,
        "Degree Mismatch": 0,
        "Location Mismatch": 0,
        "Role Mismatch": 0,
        "Department Mismatch": 0,
    }
    
    for c in candidates:
        scores = c.get("scores", {})
        if not scores:
            continue
        
        status = scores.get("status", "")
        if status != "Rejected":
            continue
        
        # Check decision_reasons from matching report
        decision_reasons = scores.get("decision_reasons", [])
        for reason in decision_reasons:
            reason_lower = reason.lower()
            if "skill" in reason_lower:
                reasons["Skills Missing"] += 1
            elif "experience" in reason_lower:
                reasons["Experience Mismatch"] += 1
            elif "education" in reason_lower or "degree" in reason_lower:
                reasons["Degree Mismatch"] += 1
            elif "location" in reason_lower:
                reasons["Location Mismatch"] += 1
            elif "role" in reason_lower and "skill" not in reason_lower:
                reasons["Role Mismatch"] += 1
            elif "department" in reason_lower and "role" not in reason_lower:
                reasons["Department Mismatch"] += 1
        
        # Also check mandatory_check -> failed_fields for additional context
        mandatory = scores.get("mandatory_check", {})
        if mandatory:
            failed_fields = mandatory.get("failed_fields", [])
            for field in failed_fields:
                if field == "skills":
                    reasons["Skills Missing"] += 1
                elif field == "experience":
                    reasons["Experience Mismatch"] += 1
                elif field == "education":
                    reasons["Degree Mismatch"] += 1
                elif field == "location":
                    reasons["Location Mismatch"] += 1
                elif field == "role":
                    reasons["Role Mismatch"] += 1
                elif field == "department":
                    reasons["Department Mismatch"] += 1
    
    return reasons
