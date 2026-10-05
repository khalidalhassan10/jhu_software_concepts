"""Flask web layer: the Analysis page plus the Pull Data and Update Analysis endpoints.

Everything is built by ``create_app(...)`` so a test can
make its own app with fake scraper / loader / query functions and its own database.
Run: ``flask --app src.flask_app:create_app run`` (from module_5, database settings exported).
"""


import threading

import psycopg
import urllib3
from flask import Flask, jsonify, redirect, render_template, request, url_for
from sqlalchemy.exc import SQLAlchemyError

from src import pull_data
from src.db_config import clamp_limit, get_database_url
from src.load_data import insert_rows
from src.models import create_session_factory
from src.orm_queries import run_analyses
from src.query_data import SEARCH_FIELDS, search_applicants


PULL_ERRORS = (RuntimeError, OSError, psycopg.Error, urllib3.exceptions.HTTPError)
QUERY_ERRORS = (RuntimeError, psycopg.Error, SQLAlchemyError)


class PullState:
    """Whether a pull is running, the last pull's result, and the last analysis read."""

    def __init__(self):
        self._lock = threading.Lock()
        self.busy = False
        self.last_result = None
        self.analysis = None

    def start(self):
        """Claim the busy flag. Returns False if a pull is already running."""
        with self._lock:
            if self.busy:
                return False
            self.busy = True
            return True

    def finish(self, result):
        """Release the busy flag and remember how the pull ended."""
        with self._lock:
            self.busy = False
            self.last_result = result


def fmt_count(value):
    """Format a count with thousands separators, or ``n/a``."""
    return "n/a" if value is None else f"{int(value):,}"


def fmt_avg(value):
    """Format an average with two decimals, or ``n/a``."""
    return "n/a" if value is None else f"{float(value):.2f}"


def fmt_pct(value):
    """Format a percentage with exactly two decimals and ``%``, or ``n/a``."""
    return "n/a" if value is None else f"{float(value):.2f}%"


def format_analysis(result):
    """Turn the ``run_analyses`` dictionary into ``(question, "Answer: ...")`` pairs.

    :param result: the dictionary returned by ``orm_queries.run_analyses``.
    :returns: a list of ``(label, answer)`` tuples, one per displayed answer.
    """
    gpa, gre, gre_v, gre_aw = result["q3"]
    shares = {degree: (count, pct) for degree, count, pct in result["q10"]}
    total = result["q10_total"]
    acc_n, acc_avg, rej_n, rej_avg = result["q11"]

    def share(degree):
        if degree not in shares:
            return "n/a"
        count, pct = shares[degree]
        return f"{fmt_count(count)} of {fmt_count(total)} ({fmt_pct(pct)})"

    gpa_gap = None if acc_avg is None or rej_avg is None else f"{acc_avg - rej_avg:+.2f}"
    items = [
        ("Q1. Fall 2026 applicant count", fmt_count(result["q1"])),
        ("Q2. Percent international", fmt_pct(result["q2"])),
        ("Q3. Average GPA", fmt_avg(gpa)),
        ("Q3. Average GRE Quantitative", fmt_avg(gre)),
        ("Q3. Average GRE Verbal", fmt_avg(gre_v)),
        ("Q3. Average GRE Analytical Writing", fmt_avg(gre_aw)),
        ("Q4. Average GPA of American applicants, Fall 2026", fmt_avg(result["q4"])),
        ("Q5. Fall 2025 acceptance percentage", fmt_pct(result["q5"])),
        ("Q6. Average GPA of accepted applicants, Fall 2026", fmt_avg(result["q6"])),
        ("Q7. JHU Computer Science master's entries", fmt_count(result["q7"])),
        ("Q8. Accepted Fall 2026 CS PhD entries at Georgetown, MIT, Stanford, CMU "
         "(original fields)",
         fmt_count(result["q8"])),
        ("Q9. The same count using the LLM-generated fields", fmt_count(result["q9"])),
        ("Q9. Difference (LLM minus original)", f"{result['q9'] - result['q8']:+d}"),
        ("Q10. Fall 2026 CS entries that are Masters", share("Masters")),
        ("Q10. Fall 2026 CS entries that are PhD", share("PhD")),
        ("Q11. Accepted Fall 2026 CS master's entries: average GPA",
         f"{fmt_avg(acc_avg)} (n={fmt_count(acc_n)})"),
        ("Q11. Rejected Fall 2026 CS master's entries: average GPA",
         f"{fmt_avg(rej_avg)} (n={fmt_count(rej_n)})"),
        ("Q11. GPA difference (accepted minus rejected)", gpa_gap or "n/a"),
    ]
    return [(label, f"Answer: {answer}") for label, answer in items]


def default_scraper(database_url):
    """Return a no-argument scraper that finds entries newer than the database."""
    def scraper():
        return pull_data.scrape_new(
            lambda ids: pull_data.existing_ids(ids, database_url), pull_data.live_fetcher()
        )
    return scraper


def default_loader(database_url):
    """Return a loader ``rows -> number inserted`` for this database."""
    def loader(rows):
        return insert_rows(rows, database_url)
    return loader


def default_query(database_url):
    """Return a no-argument query that runs the ORM analysis."""
    session_factory = create_session_factory(database_url)
    def query():
        with session_factory() as session:
            return run_analyses(session)
    return query


def create_app(scraper=None, loader=None, query=None, database_url=None, run_in_background=True):
    """Build the Flask app.

    :param scraper: function ``() -> list of entries`` (default: live Grad Café pull).
    :param loader: function ``rows -> number inserted`` (default: insert into PostgreSQL).
    :param query: function ``() -> analysis dictionary`` (default: the ORM analysis).
    :param database_url: overrides DATABASE_URL (tests pass their test database).
    :param run_in_background: True = POST /pull-data answers 202 at once and pulls in a
        thread; False = it pulls first and answers 200 (tests use False).
    :returns: the configured ``Flask`` app.
    """
    app = Flask(__name__)
    url = get_database_url(database_url)
    scraper = scraper or default_scraper(url)
    loader = loader or default_loader(url)
    query = query or default_query(url)
    state = PullState()
    app.config.update(DATABASE_URL=url, PULL_STATE=state)

    def run_pull():
        try:
            inserted = loader(scraper())
            state.finish({"ok": True, "inserted": inserted})
        except PULL_ERRORS as error:
            state.finish({"ok": False, "error": str(error)})

    @app.get("/")
    def index():
        return redirect(url_for("analysis"))

    @app.get("/analysis")
    def analysis():
        error = None
        if state.analysis is None:
            try:
                state.analysis = query()
            except QUERY_ERRORS:
                app.logger.exception("Could not read the database")
                error = "Could not read the database. Check that PostgreSQL is running."
        results = format_analysis(state.analysis) if state.analysis is not None else []
        return render_template("analysis.html", results=results, busy=state.busy,
                               last_result=state.last_result, error=error)

    @app.post("/pull-data")
    def pull_data_route():
        if not state.start():
            return jsonify({"busy": True}), 409
        if run_in_background:
            threading.Thread(target=run_pull, daemon=True).start()
            return jsonify({"ok": True}), 202
        run_pull()
        return jsonify(state.last_result), (200 if state.last_result["ok"] else 500)

    @app.post("/update-analysis")
    def update_analysis():
        if state.busy:
            return jsonify({"busy": True}), 409
        try:
            state.analysis = query()
        except QUERY_ERRORS as exc:
            return jsonify({"ok": False, "error": str(exc)}), 500
        return jsonify({"ok": True}), 200

    @app.get("/api/applicants")
    def api_applicants():
        filters = {field: request.args.get(field, "") for field in SEARCH_FIELDS}
        sort = request.args.get("sort", "p_id")
        limit = clamp_limit(request.args.get("limit"))
        try:
            rows = search_applicants(filters, sort, limit, url)
        except QUERY_ERRORS:
            return jsonify({"ok": False, "error": "Could not run the search."}), 500
        return jsonify({"ok": True, "limit": limit, "count": len(rows), "results": rows}), 200

    return app


if __name__ == "__main__":
    create_app().run(debug=False, use_reloader=False)
