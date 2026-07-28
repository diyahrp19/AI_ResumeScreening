"""
auth_db.py
----------
Simple SQLite persistence for authentication.
Stores username, email, and password locally.
No password hashing — simple auth for UI purposes only.
"""

import os
import sqlite3
from typing import Optional
from datetime import datetime

DB_PATH = os.environ.get(
    "AI_RESUME_DB_PATH",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database", "database.db"),
)


def _get_connection() -> sqlite3.Connection:
    """Get a connection to the shared SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_auth_db():
    """Create the users table if it doesn't exist."""
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def create_user(username: str, email: str, password: str) -> bool:
    """
    Create a new user account. Stores password as plain text (UI-only auth).

    Returns True on success, False if username or email already exists.
    """
    conn = _get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO users (username, email, password, created_at) VALUES (?, ?, ?, ?)",
            (username, email, password, datetime.now().isoformat()),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def get_user_by_username(username: str) -> Optional[dict]:
    """Fetch a user by username."""
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_email(email: str) -> Optional[dict]:
    """Fetch a user by email."""
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = ?", (email,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def validate_credentials(username: str, password: str) -> Optional[dict]:
    """
    Validate login credentials.

    Returns the user dict on success, None on failure.
    """
    user = get_user_by_username(username)
    if user is None:
        return None
    if user["password"] == password:
        return {"id": user["id"], "username": user["username"], "email": user["email"]}
    return None


def is_username_taken(username: str) -> bool:
    """Check if a username is already taken."""
    return get_user_by_username(username) is not None


def is_email_taken(email: str) -> bool:
    """Check if an email is already taken."""
    return get_user_by_email(email) is not None

