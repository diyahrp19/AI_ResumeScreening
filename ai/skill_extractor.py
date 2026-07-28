"""
skill_extractor.py
-------------------
NLP layer responsible for turning raw resume text into structured
information: skills, education, certifications, and projects.

Uses NLTK for tokenization / stop-word removal and a keyword-matching
approach (with alias resolution) against the skill taxonomy in
knowledge_base.py. This keyword + NLP-preprocessing combination is a
standard, explainable technique for resume screening systems.
"""

import re
from typing import List

import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords

from ai.knowledge_base import ALL_SKILLS, SKILL_ALIASES, EDUCATION_RANK, DEGREE_KEYWORDS, TECHNICAL_SKILLS, SOFT_SKILLS


def ensure_nltk_data():
    """Download required NLTK corpora if not already present (idempotent)."""
    resources = {
        "tokenizers/punkt": "punkt",
        "tokenizers/punkt_tab": "punkt_tab",
        "corpora/stopwords": "stopwords",
    }
    for path, name in resources.items():
        try:
            nltk.data.find(path)
        except LookupError:
            try:
                nltk.download(name, quiet=True)
            except Exception:  # noqa: BLE001
                pass  # Degrade gracefully; tokenize_and_clean has a regex fallback.


def tokenize_and_clean(text: str) -> List[str]:
    """Lowercase, tokenize, and strip stop-words/punctuation from text."""
    if not text or not isinstance(text, str):
        return []
    
    text = text.lower()
    try:
        tokens = word_tokenize(text)
    except Exception:  # noqa: BLE001
        tokens = re.findall(r"[a-zA-Z0-9+#\.\-]+", text)

    try:
        stop_words = set(stopwords.words("english"))
    except Exception:  # noqa: BLE001
        stop_words = set()

    cleaned = [t for t in tokens if t.isalnum() or t in ("c++", "c#")]
    cleaned = [t for t in cleaned if t not in stop_words and len(t) > 1]
    return cleaned


def _normalize_skill(raw: str) -> str:
    """
    Normalize a single skill string the same way resume text is
    normalized before matching: lowercase, strip surrounding
    whitespace/punctuation, and convert hyphen/underscore/slash word
    separators to spaces (so "Machine-Learning" typed into the Job
    Description form matches "machine learning" found in a resume).
    Known aliases (e.g. "ml") are resolved to their canonical name.
    """
    if not raw or not isinstance(raw, str):
        return ""
    
    # Convert to lowercase and strip whitespace/punctuation
    raw = raw.lower().strip()
    raw = raw.strip(".,;:!@#$%^&*()[]{}|\\/<>~`")
    
    # Normalize word separators (hyphen/underscore/slash) to spaces
    raw = re.sub(r"(?<=[a-z0-9])[-_/](?=[a-z0-9])", " ", raw)
    
    # Collapse multiple spaces
    raw = re.sub(r"\s+", " ", raw).strip()
    
    # Return canonical name if it's an alias, otherwise return normalized
    return SKILL_ALIASES.get(raw, raw)


def extract_technical_skills(text: str) -> List[str]:
    """Extract only technical skills from text."""
    all_skills = extract_skills(text)
    return [s for s in all_skills if s in TECHNICAL_SKILLS]


def extract_soft_skills(text: str) -> List[str]:
    """Extract only soft skills from text."""
    all_skills = extract_skills(text)
    return [s for s in all_skills if s in SOFT_SKILLS]


def extract_skills(text: str) -> List[str]:
    """
    Keyword-match the resume text against the canonical skill taxonomy.
    Multi-word skills (e.g. "machine learning") are matched via phrase
    search; single-word / symbol skills (e.g. "c++") via token search.

    Before matching, the text is normalized so common punctuation
    variants of the same skill converge on one canonical form:
      - case is ignored (already lowercased)
      - hyphens/underscores/slashes between words become spaces, so
        "machine-learning", "machine_learning", and "machine learning"
        all match the same taxonomy entry
      - repeated whitespace collapses to single spaces
    Symbol-bearing skills that legitimately contain punctuation (c++,
    c#, node.js, asp.net) are unaffected since only *separator*
    punctuation between alphanumeric words is normalized, not "+", "#"
    or ".".
    """
    if not text or not isinstance(text, str):
        return []
    
    # Normalize text: lowercase, replace newlines, add spaces for word boundary matching
    text_lower = " " + text.lower().replace("\n", " ") + " "
    
    # Normalize word separators (hyphen/underscore/slash) to spaces so
    # punctuation variants of the same skill converge before matching.
    text_lower = re.sub(r"(?<=[a-z0-9])[-_/](?=[a-z0-9])", " ", text_lower)
    
    # Remove special characters except those that are part of skills (+, #, .)
    text_lower = re.sub(r"[^\w\s\+\#\.\-]", " ", text_lower)
    
    # Collapse extra whitespace for reliable phrase matching
    text_lower = re.sub(r"\s+", " ", text_lower)

    found = set()

    # Direct phrase search across the full taxonomy (handles multi-word skills)
    for skill in ALL_SKILLS:
        # Use word boundary pattern for more accurate matching
        pattern = r"(?<![a-zA-Z0-9])" + re.escape(skill) + r"(?![a-zA-Z0-9])"
        if re.search(pattern, text_lower):
            found.add(skill)

    # Alias search (also benefits from the same separator normalization,
    # so "ml" or "machine_learning" both resolve to "machine learning")
    for alias, canonical in SKILL_ALIASES.items():
        pattern = r"(?<![a-zA-Z0-9])" + re.escape(alias) + r"(?![a-zA-Z0-9])"
        if re.search(pattern, text_lower):
            found.add(canonical)

    # Additional pattern matching for common variations
    # Match "AI" as "artificial intelligence"
    if re.search(r'\bai\b', text_lower) and "artificial intelligence" in ALL_SKILLS:
        found.add("artificial intelligence")
    
    # Return a clean, sorted, unique list.
    return sorted(found)


def extract_education(text: str) -> List[str]:
    """Return degree mentions found in the text, ordered by rank (highest first)."""
    if not text or not isinstance(text, str):
        return []
    
    text_lower = text.lower()
    found = []
    
    # Look for education keywords with more flexible matching
    for degree in DEGREE_KEYWORDS:
        # Use word boundary pattern
        pattern = r"(?<![a-zA-Z])" + re.escape(degree) + r"(?![a-zA-Z])"
        if re.search(pattern, text_lower):
            found.append(degree)
    
    # Also look for common abbreviations and variations
    education_patterns = [
        (r"\bb\.?tech\b", "b.tech"),
        (r"\bm\.?tech\b", "m.tech"),
        (r"\bb\.?e\b", "b.e"),
        (r"\bm\.?e\b", "m.e"),
        (r"\bb\.?sc\b", "bsc"),
        (r"\bm\.?sc\b", "msc"),
        (r"\bb\.?a\b", "b.a"),
        (r"\bm\.?a\b", "m.a"),
        (r"\bm\.?b\.?a\b", "mba"),
        (r"\bph\.?d\b", "phd"),
        (r"\bdoctorate\b", "doctorate"),
    ]
    
    for pattern, degree_name in education_patterns:
        if re.search(pattern, text_lower) and degree_name not in found:
            found.append(degree_name)
    
    # Remove duplicates and sort by rank (highest first)
    found = sorted(set(found), key=lambda d: -EDUCATION_RANK.get(d, 0))
    return found


def highest_education_rank(education_list: List[str]) -> int:
    if not education_list:
        return 0
    return max(EDUCATION_RANK.get(e, 0) for e in education_list)


def extract_certifications(section_text: str, full_text: str) -> List[str]:
    """
    Pull certification lines. Prefers the segmented 'certifications'
    section; falls back to scanning the full text for lines containing
    'certified' / 'certification'.
    """
    lines = []
    source = section_text if section_text.strip() else full_text
    for line in source.split("\n"):
        clean = line.strip(" -\u2022\t")
        if not clean:
            continue
        if section_text.strip() or re.search(r"certifi", clean, re.IGNORECASE):
            if 3 <= len(clean) <= 120:
                lines.append(clean)
    # de-duplicate while preserving order
    seen = set()
    result = []
    for l in lines:
        if l.lower() not in seen:
            seen.add(l.lower())
            result.append(l)
    return result[:15]


def extract_projects(section_text: str) -> List[str]:
    """Extract project bullet lines from the 'projects' section."""
    if not section_text.strip():
        return []
    lines = []
    for line in section_text.split("\n"):
        clean = line.strip(" -\u2022\t")
        if clean and 3 <= len(clean) <= 200:
            lines.append(clean)
    return lines[:15]



