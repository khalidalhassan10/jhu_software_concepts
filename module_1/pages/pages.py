"""Blueprint containing the route for each page of the site."""
from flask import Blueprint, render_template

# Groups all page routes under one blueprint. Endpoints become
# "pages.home", "pages.projects", "pages.contact".
bp = Blueprint("pages", __name__)


@bp.route("/")
def home():
    """Homepage: name, position, bio, and photo."""
    return render_template("home.html")


@bp.route("/projects")
def projects():
    """Projects page: Module 1 project details and GitHub link."""
    return render_template("projects.html")


@bp.route("/contact")
def contact():
    """Contact page: email address and LinkedIn."""
    return render_template("contact.html")