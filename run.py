"""
run.py
------
Entry point to run the Flask application.
Usage: python run.py
"""

from app import create_app

app = create_app()

if __name__ == "__main__":
    print("=" * 60)
    print("  AI Resume Screening System - Flask")
    print("  Open http://127.0.0.1:5000 in your browser")
    print("=" * 60)
    app.run(debug=True, host="0.0.0.0", port=5000)

