"""Flask webpage for the Grad Café analysis."""
import os
import subprocess
import sys
import threading
from pathlib import Path

from flask import Flask, flash, redirect, render_template, url_for

from models import create_session_factory
from orm_queries import run_analyses


app = Flask(__name__)
app.secret_key = os.urandom(32)

ROOT = Path(__file__).resolve().parent
Session = create_session_factory()

lock = threading.Lock()
state = {"pulling": False, "notice": ""}


def pull_worker():
    try:
        process = subprocess.run(
            [sys.executable, str(ROOT / "pull_data.py")],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=20 * 60,
            check=False,
        )

        output = process.stdout if process.returncode == 0 else process.stderr
        lines = output.strip().splitlines()
        message = lines[-1] if lines else "Pull finished without a status message."

    except subprocess.TimeoutExpired:
        message = (
            "Pull took over 20 minutes and was stopped. "
            "Already committed pages remain saved."
        )
    except OSError as exc:
        message = f"Could not start the pull: {exc}"

    with lock:
        state["notice"] = message
        state["pulling"] = False


@app.get("/")
def index():
    try:
        with Session() as session:
            results = run_analyses(session)
    except Exception as exc:
        results = None
        flash(
            f"Could not read the database: {exc}. "
            "Check PostgreSQL and PGPASSWORD."
        )

    with lock:
        pulling = state["pulling"]
        notice = state["notice"]

    return render_template(
        "analysis.html",
        r=results,
        pulling=pulling,
        notice=notice,
    )


@app.post("/pull")
def pull():
    with lock:
        if state["pulling"]:
            flash("A Pull Data request is already running; wait for it to finish.")
            return redirect(url_for("index"))

        state["pulling"] = True
        state["notice"] = "Pulling the newest Grad Café entries now."

    threading.Thread(target=pull_worker, daemon=True).start()
    return redirect(url_for("index"))


@app.post("/refresh")
def refresh():
    with lock:
        pulling = state["pulling"]

    if pulling:
        flash(
            "Analysis updated from the database. "
            "Pull Data is still retrieving entries."
        )
    else:
        flash("Analysis updated from the latest database entries.")

    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=False, use_reloader=False)