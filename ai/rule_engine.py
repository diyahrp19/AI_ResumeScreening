"""
rule_engine.py
--------------
Implements the Rule-Based Inference layer and Expert System explanation
logic described in the project spec.

Design:
    Each rule is a small function that inspects the candidate's
    extracted profile + the job description and returns a `RuleResult`
    (a notional score delta, and a human-readable explanation).
    `evaluate_rules` runs every rule and aggregates the explanations,
    which the Expert System (build_expert_recommendation) turns into a
    narrative recommendation (strengths/weaknesses/verdict).

    The decision engine uses strict IF/THEN rules:
    - IF Location Mismatch THEN Reject
    - IF Experience < Required THEN Reject
    - IF Required Degree Missing THEN Reject
    - IF Required Skills Missing (< 50%) THEN Reject
    - Only shortlist candidates who satisfy ALL mandatory requirements.
"""

from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class RuleResult:
    rule_name: str
    passed: bool
    score_delta: float
    explanation: str


@dataclass
class RuleEngineOutput:
    results: List[RuleResult] = field(default_factory=list)
    total_delta: float = 0.0

    @property
    def positive_explanations(self) -> List[str]:
        return [r.explanation for r in self.results if r.passed]

    @property
    def negative_explanations(self) -> List[str]:
        return [r.explanation for r in self.results if not r.passed]


def rule_required_skills_coverage(candidate: dict, job: dict) -> RuleResult:
    """IF candidate has >= 50% of required skills THEN pass, ELSE fail."""
    required = set(job.get("skills", []))
    have = set(candidate.get("skills", []))
    if not required:
        return RuleResult("required_skills_coverage", True, 0.0,
                           "No specific skills were required, so this rule was skipped.")
    coverage = len(required & have) / len(required)
    if coverage >= 0.8:
        return RuleResult(
            "required_skills_coverage", True, 8.0,
            f"Candidate covers {coverage*100:.0f}% of the required skills - strong technical fit."
        )
    elif coverage >= 0.5:
        return RuleResult(
            "required_skills_coverage", True, 3.0,
            f"Candidate covers {coverage*100:.0f}% of the required skills - moderate technical fit."
        )
    else:
        return RuleResult(
            "required_skills_coverage", False, -10.0,
            f"Candidate covers only {coverage*100:.0f}% of the required skills - significant skill gap."
        )


def rule_minimum_experience(candidate: dict, job: dict) -> RuleResult:
    """IF experience < required experience THEN reject."""
    required_exp = float(job.get("experience_years", 0) or 0)
    candidate_exp = float(candidate.get("experience_years", 0) or 0)

    if required_exp <= 0:
        return RuleResult("minimum_experience", True, 0.0,
                           "No minimum experience was specified for this role.")

    if candidate_exp >= required_exp:
        bonus = 8.0 if candidate_exp >= required_exp + 2 else 5.0
        return RuleResult(
            "minimum_experience", True, bonus,
            f"Candidate has {candidate_exp} year(s) of experience, meeting or exceeding "
            f"the required {required_exp} year(s)."
        )
    else:
        gap = required_exp - candidate_exp
        penalty = -15.0 if gap >= 2 else -8.0
        return RuleResult(
            "minimum_experience", False, penalty,
            f"Candidate has only {candidate_exp} year(s) of experience versus the required "
            f"{required_exp} year(s) - a gap of {gap:.1f} year(s)."
        )


def rule_education_match(candidate: dict, job: dict) -> RuleResult:
    """IF candidate education rank >= required rank THEN pass, ELSE fail."""
    from ai.skill_extractor import highest_education_rank
    from ai.knowledge_base import EDUCATION_RANK

    required_edu = (job.get("education") or "").lower().strip()
    if not required_edu:
        return RuleResult("education_match", True, 0.0,
                           "No specific education requirement was set for this role.")

    required_rank = 0
    for key, rank in EDUCATION_RANK.items():
        if key in required_edu:
            required_rank = max(required_rank, rank)

    candidate_rank = highest_education_rank(candidate.get("education", []))

    if required_rank == 0:
        return RuleResult("education_match", True, 0.0,
                           "Education requirement could not be matched to a standard degree level.")

    if candidate_rank >= required_rank:
        return RuleResult(
            "education_match", True, 6.0,
            "Candidate's education level meets or exceeds the job's requirement."
        )
    else:
        return RuleResult(
            "education_match", False, -6.0,
            "Candidate's education level is below the job's stated requirement."
        )


def rule_certifications_bonus(candidate: dict, job: dict) -> RuleResult:
    """IF candidate has relevant certifications THEN small bonus."""
    certs = candidate.get("certifications", [])
    if certs:
        return RuleResult(
            "certifications_bonus", True, min(5.0, len(certs) * 1.5),
            f"Candidate lists {len(certs)} certification(s), adding credibility to their profile."
        )
    return RuleResult("certifications_bonus", False, 0.0,
                       "No certifications were detected on the resume.")


def rule_projects_bonus(candidate: dict, job: dict) -> RuleResult:
    """IF candidate lists relevant projects THEN small bonus."""
    projects = candidate.get("projects", [])
    required_skills = set(job.get("skills", []))
    if not projects:
        return RuleResult("projects_bonus", False, 0.0,
                           "No project section was detected on the resume.")

    relevant = [p for p in projects if any(s in p.lower() for s in required_skills)]
    if relevant:
        return RuleResult(
            "projects_bonus", True, min(6.0, len(relevant) * 2.0),
            f"{len(relevant)} project(s) directly relate to the required skill set."
        )
    return RuleResult(
        "projects_bonus", True, 2.0,
        f"Candidate lists {len(projects)} project(s), demonstrating hands-on practice."
    )


def rule_critical_skill_missing(candidate: dict, job: dict) -> RuleResult:
    """IF a heavily-weighted/critical required skill is missing THEN penalize."""
    required = job.get("skills", [])
    if not required:
        return RuleResult("critical_skill_missing", True, 0.0, "No critical skills flagged.")

    have = set(candidate.get("skills", []))
    # Treat the first 2 listed required skills as "critical" (HR typically lists
    # the most important skills first in a job description).
    critical = required[:2]
    missing_critical = [s for s in critical if s not in have]

    if missing_critical:
        return RuleResult(
            "critical_skill_missing", False, -5.0 * len(missing_critical),
            f"Candidate is missing critical required skill(s): {', '.join(missing_critical)}."
        )
    return RuleResult("critical_skill_missing", True, 3.0,
                       "Candidate possesses all critical required skills.")


def rule_location_match(candidate: dict, job: dict) -> RuleResult:
    """IF location does not match THEN reject."""
    job_location = (job.get("location") or "").strip().lower()
    candidate_location = (candidate.get("location") or "").strip().lower()
    
    if not job_location:
        return RuleResult("location_match", True, 0.0,
                           "No location requirement was specified for this role.")
    
    if job_location in candidate_location or candidate_location in job_location:
        if candidate_location != "not found":
            return RuleResult(
                "location_match", True, 5.0,
                f"Candidate location ({candidate_location.title()}) matches required location ({job_location.title()})."
            )
    
    return RuleResult(
        "location_match", False, -10.0,
        f"Candidate location ({candidate_location.title() if candidate_location != 'not found' else 'Not Found'}) "
        f"does not match required location ({job_location.title()})."
    )


def rule_role_match(candidate: dict, job: dict) -> RuleResult:
    """IF role does not match THEN penalize."""
    job_role = (job.get("role") or job.get("title") or "").strip().lower()
    candidate_role = (candidate.get("role") or "").strip().lower()
    
    if not job_role:
        return RuleResult("role_match", True, 0.0,
                           "No role requirement was specified for this position.")
    
    if job_role in candidate_role or candidate_role in job_role:
        if candidate_role != "not found":
            return RuleResult(
                "role_match", True, 5.0,
                f"Candidate role ({candidate_role.title()}) matches required role ({job_role.title()})."
            )
    
    return RuleResult(
        "role_match", False, -8.0,
        f"Candidate role ({candidate_role.title() if candidate_role != 'not found' else 'Not Found'}) "
        f"does not match required role ({job_role.title()})."
    )


def rule_department_match(candidate: dict, job: dict) -> RuleResult:
    """IF department does not match (using smart hierarchy) THEN penalize."""
    from ai.knowledge_base import get_parent_department, departments_match
    
    job_dept = (job.get("department") or "").strip()
    candidate_dept = (candidate.get("department") or "").strip()
    
    if not job_dept:
        return RuleResult("department_match", True, 0.0,
                           "No department requirement was specified for this role.")
    
    if departments_match(job_dept, candidate_dept):
        return RuleResult(
            "department_match", True, 3.0,
            f"Candidate department ({candidate_dept.title() if candidate_dept else 'Not Found'}) "
            f"belongs to same category as required ({job_dept.title()})."
        )
    
    job_parent = get_parent_department(job_dept)
    candidate_parent = get_parent_department(candidate_dept)
    
    return RuleResult(
        "department_match", False, -5.0,
        f"Candidate department ({candidate_dept.title() if candidate_dept else 'Not Found'}) "
        f"does not match required department ({job_dept.title()}, category: {job_parent})."
    )


ALL_RULES = [
    rule_required_skills_coverage,
    rule_minimum_experience,
    rule_education_match,
    rule_certifications_bonus,
    rule_projects_bonus,
    rule_critical_skill_missing,
    rule_location_match,
    rule_role_match,
    rule_department_match,
]


def evaluate_rules(candidate: dict, job: dict) -> RuleEngineOutput:
    output = RuleEngineOutput()
    for rule_fn in ALL_RULES:
        result = rule_fn(candidate, job)
        output.results.append(result)
        output.total_delta += result.score_delta
    return output


def build_expert_recommendation(candidate: dict, job: dict, overall_score: float,
                                 missing_skills: List[str]) -> Dict:
    """
    Expert System layer: turns the rule outcomes + the (already
    computed, weighted) overall score into a structured, human-readable
    recommendation with strengths, weaknesses, and a final verdict -
    mirroring how a human recruiter would justify a shortlisting
    decision. Only two outcomes are used - Shortlisted or Rejected -
    there is no intermediate "Review" status.
    """
    rule_output = evaluate_rules(candidate, job)

    strengths = list(rule_output.positive_explanations)
    weaknesses = list(rule_output.negative_explanations)

    SHORTLIST_THRESHOLD = 60.0
    if overall_score >= SHORTLIST_THRESHOLD:
        status = "Shortlisted"
        verdict = "Strong match - recommended for interview."
    else:
        status = "Rejected"
        verdict = "Weak match - does not currently meet the role's requirements."

    if missing_skills:
        skill_note = (
            f"Candidate is suitable but requires additional knowledge in: "
            f"{', '.join(missing_skills[:6])}."
        )
    else:
        skill_note = "Candidate covers all required skills for this role."

    return {
        "status": status,
        "verdict": verdict,
        "summary": skill_note,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "rule_breakdown": [
            {"rule": r.rule_name, "passed": r.passed, "delta": r.score_delta,
             "explanation": r.explanation}
            for r in rule_output.results
        ],
    }