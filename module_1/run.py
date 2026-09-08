"""Entry point for the Module 1 personal website.

Run with:  python run.py
Then open: http://localhost:8080
"""
from flask import Flask

from pages.pages import bp as pages_bp


def create_app():
    """Create the Flask application and register the pages blueprint."""
    app = Flask(__name__)
    app.register_blueprint(pages_bp)
    return app


app = create_app()

if __name__ == "__main__":
    # 0.0.0.0 makes the site reachable as localhost too; port 8080 per assignment.
    app.run(host="0.0.0.0", port=8080)