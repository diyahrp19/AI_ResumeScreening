"""
config.py
---------
Application configuration for the Flask-based AI Resume Screening System.
"""

import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "ai-resume-screening-secret-key-change-in-production")
    
    # Database
    DB_PATH = os.path.join(BASE_DIR, "database", "database.db")
    
    # Uploads
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload
    
    # Allowed extensions
    ALLOWED_EXTENSIONS = {".pdf", ".docx"}
    
    # Session (using CacheLib backend per flask-session 0.8+)
    SESSION_TYPE = "cachelib"
    SESSION_PERMANENT = False
    
    # Education options for job description form
    EDUCATION_OPTIONS = [
        "High School", "Diploma", "Bachelor's Degree", "Master's Degree", "PhD", "Other",
    ]
    
    # Classification thresholds
    SHORTLIST_THRESHOLD = 60.0
    MIN_SKILL_MATCH = 0.5
    
    # ATS Weights
    ATS_WEIGHTS = {
        "skill": 0.40,
        "experience": 0.20,
        "education": 0.10,
        "role": 0.10,
        "department": 0.05,
        "location": 0.10,
        "projects": 0.03,
        "certifications": 0.02,
    }

