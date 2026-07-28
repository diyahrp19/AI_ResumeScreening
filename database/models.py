"""
models.py
---------
SQLite persistence layer. Stores job descriptions, candidate
screening results, activity logs, and report history with
user_id associations so each user sees only their own data.

All functions open/close their own connection for thread safety.
"""

import json
import logging
import os
import sqlite3
from datetime import datetime
from typing import List, Optional

DB_PATH = os.environ.get(
    "AI_RESUME_DB_PATH",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database", "database.db"),
)


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()
    
    # Migrate: Add user_id columns if they don't exist
    # Check if user_id column exists in job_descriptions
    cur.execute("PRAGMA table_info(job_descriptions)")
    cols = {row["name"] for row in cur.fetchall()}
    
    # Create job_descriptions table if not exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS job_descriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT,
            skills TEXT,
            experience_years REAL,
            education TEXT,
            department TEXT,
            location TEXT,
            created_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    # Create candidates table if not exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            job_id INTEGER,
            filename TEXT,
            name TEXT,
            email TEXT,
            phone TEXT,
            education TEXT,
            experience_years REAL,
            skills TEXT,
            certifications TEXT,
            projects TEXT,
            raw_text TEXT,
            file_hash TEXT,
            location TEXT,
            scores TEXT,
            upload_time TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (job_id) REFERENCES job_descriptions (id)
        )
    """)
    
    # Add user_id column to job_descriptions if upgrading
    try:
        cur.execute("ALTER TABLE job_descriptions ADD COLUMN user_id INTEGER REFERENCES users(id)")
    except sqlite3.OperationalError:
        pass  # column already exists
    
    # Add user_id column to candidates if upgrading
    try:
        cur.execute("ALTER TABLE candidates ADD COLUMN user_id INTEGER REFERENCES users(id)")
    except sqlite3.OperationalError:
        pass  # column already exists
    
    # Add file_hash column if upgrading from an older schema
    try:
        cur.execute("ALTER TABLE candidates ADD COLUMN file_hash TEXT")
    except sqlite3.OperationalError:
        pass  # column already exists
    
    # Create activity_log table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            details TEXT,
            candidate_name TEXT,
            status TEXT,
            timestamp TEXT NOT NULL,
            display_time TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    # Create report_history table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS report_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            format TEXT NOT NULL,
            job_title TEXT,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    # Create users table for authentication (simple, UI-only auth)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    
    # Create indexes for better query performance
    try:
        cur.execute("CREATE INDEX IF NOT EXISTS idx_candidates_file_hash ON candidates(file_hash)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_candidates_upload_time ON candidates(upload_time)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_candidates_user_id ON candidates(user_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_job_descriptions_created_at ON job_descriptions(created_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_job_descriptions_user_id ON job_descriptions(user_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_activity_log_user_id ON activity_log(user_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_activity_log_timestamp ON activity_log(timestamp)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_report_history_user_id ON report_history(user_id)")
    except sqlite3.OperationalError:
        pass  # indexes may already exist
    
    conn.commit()
    conn.close()


# ====================================================================
# USER HELPERS
# ====================================================================

def get_user_by_id(user_id: int) -> Optional[dict]:
    """Fetch a user by their ID."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


# ====================================================================
# JOB DESCRIPTION FUNCTIONS
# ====================================================================

def save_job_description(job: dict, user_id: Optional[int] = None) -> int:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO job_descriptions (user_id, title, skills, experience_years, education,
                                           department, location, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            job.get("title", ""),
            json.dumps(job.get("skills", [])),
            job.get("experience_years", 0),
            job.get("education", ""),
            job.get("department", ""),
            job.get("location", ""),
            datetime.now().isoformat(),
        ))
        conn.commit()
        job_id = cur.lastrowid
        return job_id
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to save job description: {e}")
        raise
    finally:
        conn.close()


def get_job_descriptions_by_user(user_id: int) -> List[dict]:
    """Get all job descriptions for a specific user, newest first."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM job_descriptions WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        )
        rows = cur.fetchall()
        results = []
        for row in rows:
            d = dict(row)
            d["skills"] = json.loads(d["skills"] or "[]")
            results.append(d)
        return results
    finally:
        conn.close()


def get_latest_job_description(user_id: int) -> Optional[dict]:
    """Get the most recent job description for a user."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM job_descriptions WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
            (user_id,),
        )
        row = cur.fetchone()
        if row:
            d = dict(row)
            d["skills"] = json.loads(d["skills"] or "[]")
            return d
        return None
    finally:
        conn.close()


# ====================================================================
# CANDIDATE FUNCTIONS
# ====================================================================

def save_candidate(candidate: dict, user_id: Optional[int] = None, job_id: Optional[int] = None) -> int:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO candidates (user_id, job_id, filename, name, email, phone, education,
                                     experience_years, skills, certifications, projects,
                                     raw_text, file_hash, location, scores, upload_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            job_id,
            candidate.get("filename", ""),
            candidate.get("name", ""),
            candidate.get("email", ""),
            candidate.get("phone", ""),
            json.dumps(candidate.get("education", [])),
            candidate.get("experience_years", 0),
            json.dumps(candidate.get("skills", [])),
            json.dumps(candidate.get("certifications", [])),
            json.dumps(candidate.get("projects", [])),
            candidate.get("raw_text", ""),
            candidate.get("file_hash", ""),
            candidate.get("location", ""),
            json.dumps(candidate.get("scores", {})),
            candidate.get("upload_time", datetime.now().isoformat()),
        ))
        conn.commit()
        candidate_id = cur.lastrowid
        return candidate_id
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to save candidate '{candidate.get('name', 'Unknown')}': {e}")
        raise
    finally:
        conn.close()


def update_candidate_scores(file_hash: str, scores: dict, user_id: Optional[int] = None) -> bool:
    """Update an existing candidate's scores by file_hash (scoped to user)."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        if user_id:
            cur.execute(
                "UPDATE candidates SET scores = ? WHERE file_hash = ? AND user_id = ?",
                (json.dumps(scores), file_hash, user_id),
            )
        else:
            cur.execute(
                "UPDATE candidates SET scores = ? WHERE file_hash = ?",
                (json.dumps(scores), file_hash),
            )
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to update candidate scores: {e}")
        raise
    finally:
        conn.close()


def get_candidate_by_hash(file_hash: str, user_id: Optional[int] = None) -> Optional[dict]:
    """Check if a candidate with the given file hash already exists (scoped to user)."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        if user_id:
            cur.execute(
                "SELECT * FROM candidates WHERE file_hash = ? AND user_id = ? LIMIT 1",
                (file_hash, user_id),
            )
        else:
            cur.execute(
                "SELECT * FROM candidates WHERE file_hash = ? LIMIT 1",
                (file_hash,),
            )
        row = cur.fetchone()
        if row:
            d = dict(row)
            d["education"] = json.loads(d["education"] or "[]")
            d["skills"] = json.loads(d["skills"] or "[]")
            d["certifications"] = json.loads(d["certifications"] or "[]")
            d["projects"] = json.loads(d["projects"] or "[]")
            d["scores"] = json.loads(d["scores"] or "{}")
            return d
        return None
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to get candidate by hash: {e}")
        return None
    finally:
        conn.close()


def get_candidates_by_user(user_id: int) -> List[dict]:
    """Get all candidates for a specific user, newest first."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM candidates WHERE user_id = ? ORDER BY upload_time DESC",
            (user_id,),
        )
        rows = cur.fetchall()
        results = []
        for row in rows:
            d = dict(row)
            d["education"] = json.loads(d["education"] or "[]")
            d["skills"] = json.loads(d["skills"] or "[]")
            d["certifications"] = json.loads(d["certifications"] or "[]")
            d["projects"] = json.loads(d["projects"] or "[]")
            d["scores"] = json.loads(d["scores"] or "{}")
            results.append(d)
        return results
    finally:
        conn.close()


# ====================================================================
# ACTIVITY LOG FUNCTIONS
# ====================================================================

def save_activity_log(user_id: int, action: str, details: str,
                      candidate_name: str = "", status: str = "") -> int:
    """Save an activity log entry for a user."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        now = datetime.now()
        cur.execute("""
            INSERT INTO activity_log (user_id, action, details, candidate_name, status, timestamp, display_time)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            action,
            details,
            candidate_name,
            status or "success",
            now.isoformat(timespec="seconds"),
            now.strftime("%Y-%m-%d %H:%M"),
        ))
        conn.commit()
        return cur.lastrowid
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to save activity log: {e}")
        raise
    finally:
        conn.close()


def get_activity_log_by_user(user_id: int, limit: int = 100) -> List[dict]:
    """Get activity log entries for a user, newest first."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM activity_log WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
            (user_id, limit),
        )
        rows = cur.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


# ====================================================================
# REPORT HISTORY FUNCTIONS
# ====================================================================

def save_report_history(user_id: int, fmt: str, job_title: str = "") -> int:
    """Save a report history entry for a user."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO report_history (user_id, format, job_title, timestamp)
            VALUES (?, ?, ?, ?)
        """, (
            user_id,
            fmt,
            job_title or "Untitled Role",
            datetime.now().isoformat(timespec="seconds"),
        ))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_report_history_by_user(user_id: int, limit: int = 50) -> List[dict]:
    """Get report history for a user, newest first."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM report_history WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
            (user_id, limit),
        )
        rows = cur.fetchall()
        results = []
        for row in rows:
            d = dict(row)
            # Format display timestamp
            try:
                ts = datetime.fromisoformat(d["timestamp"])
                d["display_time"] = ts.strftime("%Y-%m-%d %H:%M")
            except (ValueError, TypeError):
                d["display_time"] = d["timestamp"]
            results.append(d)
        return results
    finally:
        conn.close()


# ====================================================================
# CLEAR DATA FUNCTIONS
# ====================================================================

def clear_user_data(user_id: int) -> None:
    """Delete ALL data for a specific user (candidates, job descriptions, activity logs, report history).
    This is the 'Clear All Data' operation and cannot be undone.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM candidates WHERE user_id = ?", (user_id,))
        cur.execute("DELETE FROM job_descriptions WHERE user_id = ?", (user_id,))
        cur.execute("DELETE FROM activity_log WHERE user_id = ?", (user_id,))
        cur.execute("DELETE FROM report_history WHERE user_id = ?", (user_id,))
        conn.commit()
        logger = logging.getLogger(__name__)
        logger.info(f"All data cleared for user_id={user_id}")
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to clear user data: {e}")
        raise
    finally:
        conn.close()


def clear_all_data():
    """Delete ALL data from all tables (admin use only)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM candidates")
    cur.execute("DELETE FROM job_descriptions")
    cur.execute("DELETE FROM activity_log")
    cur.execute("DELETE FROM report_history")
    conn.commit()
    conn.close()

