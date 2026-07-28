"""
app.py
------
Flask application factory for the AI Resume Screening System.
Loads NLP models once at startup, registers blueprints, and
initializes the database.
"""

import os
import sys
import logging
from flask import Flask
from flask_session import Session
from cachelib.file import FileSystemCache

from config import Config
from database import models
from auth.auth_db import init_auth_db


def setup_logging(app):
    """Configure application-wide logging."""
    log_level = logging.DEBUG if app.debug else logging.INFO
    log_format = "[%(asctime)s] %(levelname)s [%(name)s] %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter(log_format, date_format))
    root_logger.addHandler(console_handler)

    # File handler (rotate at 10MB)
    try:
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
        os.makedirs(log_dir, exist_ok=True)
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            os.path.join(log_dir, "app.log"),
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter(log_format, date_format))
        root_logger.addHandler(file_handler)
    except Exception as e:
        print(f"[WARN] Could not set up file logging: {e}", file=sys.stderr)

    # Suppress noisy library loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    logging.getLogger("nltk").setLevel(logging.WARNING)
    logging.getLogger("spacy").setLevel(logging.WARNING)

    app.logger = logging.getLogger("app")
    app.logger.info("Logging initialized.")


def create_app(config_class=Config):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Setup logging first
    setup_logging(app)
    logger = app.logger

    # Ensure upload directory exists
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Initialize database
    try:
        models.init_db()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.warning(f"Database initialization failed: {e}")

    try:
        init_auth_db()
        logger.info("Auth database initialized successfully.")
    except Exception as e:
        logger.warning(f"Auth database initialization failed: {e}")

    # Server-side session (using CacheLib backend to avoid deprecation warnings)
    session_dir = os.path.join(app.instance_path, "flask_session")
    os.makedirs(session_dir, exist_ok=True)
    app.config["SESSION_CACHELIB"] = FileSystemCache(
        cache_dir=session_dir,
        threshold=500,
        mode=0o600,
    )
    Session(app)

    # Load NLP resources at startup (once, shared across all requests)
    from ai.skill_extractor import ensure_nltk_data
    ensure_nltk_data()

    # Register blueprints
    from routes.auth_routes import auth_bp
    from routes.main_routes import main_bp
    from routes.screening_routes import screening_bp
    from routes.candidates_routes import candidates_bp
    from routes.reports_routes import reports_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(screening_bp)
    app.register_blueprint(candidates_bp)
    app.register_blueprint(reports_bp)

    # Inject NLP model into app config for global access
    _load_nlp_model(app, logger)

    return app


def _load_nlp_model(app, logger=None):
    """Load spaCy model once at startup; store in app config."""
    if logger is None:
        logger = logging.getLogger("app")
    try:
        import spacy
        nlp = spacy.load("en_core_web_sm")
        app.config["NLP_MODEL"] = nlp
        logger.info("spaCy NER model loaded successfully.")
    except Exception as e:
        app.config["NLP_MODEL"] = None
        logger.info(f"spaCy model not available, using regex fallback. ({e})")


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)

