"""Shared fixtures: every test file in tests/ can ask for these by name.

pytest loads conftest.py automatically, so test files never import it: they ask for a
fixture by writing its name as a test parameter.
"""
import os

import psycopg
import pytest

from src.flask_app import create_app
from src.load_data import ensure_table


SAMPLE_RESULT = {
    "q1": 19290, "q2": 50.0949, "q3": (3.7871, 164.8778, 160.38, 5.17),
    "q4": 3.79, "q5": 39.2847, "q6": 3.78, "q7": 8, "q8": 28, "q9": 32,
    "q10_total": 1679, "q10": [("Masters", 569, 33.8892), ("PhD", 1109, 66.0512)],
    "q11": (280, 3.85, 122, 3.74),
}

SAMPLE_ROWS = [
    {"url": "https://www.thegradcafe.com/result/1", "program": "Computer Science, MIT", "term": "Fall 2026"},
    {"url": "https://www.thegradcafe.com/result/2", "program": "Physics, Stanford University", "term": "Fall 2026"},
]


@pytest.fixture()
def fake_query():
    """A query that returns SAMPLE_RESULT and counts its calls in query.calls."""
    def query():
        query.calls += 1
        return SAMPLE_RESULT
    query.calls = 0
    return query


@pytest.fixture()
def fake_scraper():
    """A scraper that returns SAMPLE_ROWS instantly: no internet."""
    def scraper():
        return SAMPLE_ROWS
    return scraper


@pytest.fixture()
def recording_loader():
    """A loader that writes nothing: it remembers the rows it got in loader.calls."""
    def loader(rows):
        loader.calls.append(rows)
        return len(rows)
    loader.calls = []
    return loader


@pytest.fixture()
def app(fake_scraper, recording_loader, fake_query):
    """The app, built with the three fakes. No database, no internet.

    run_in_background=False: POST /pull-data finishes the pull before answering (200),
    so tests never have to wait.
    """
    app = create_app(scraper=fake_scraper, loader=recording_loader, query=fake_query,
                     database_url="postgresql://unused", run_in_background=False)
    app.config["TESTING"] = True
    yield app


@pytest.fixture()
def client(app):
    """A browser that talks to the app without a real server."""
    return app.test_client()


def build_row(result_id, **changes):
    """Return one scraped Grad Café record whose URL ends in ``result_id``."""
    row = {
        "url": f"https://www.thegradcafe.com/result/{result_id}",
        "program": "Computer Science, Johns Hopkins University",
        "comments": "",
        "date_added": "Sep 12, 2026",
        "status": "Accepted on Sep 11",
        "term": "Fall 2026",
        "US/International": "International",
        "GPA": "3.80",
        "GRE": "", "GRE V": "", "GRE AW": "",
        "Degree": "Masters",
        "llm-generated-program": "Computer Science",
        "llm-generated-university": "Johns Hopkins University",
    }
    row.update(changes)
    return row


DB_ROWS = [
    build_row(1),
    build_row(2, **{"US/International": "American"}),
    build_row(3, term="Fall 2025", status="Rejected on Aug 01", GPA=""),
]


@pytest.fixture()
def make_row():
    """Give a test the record builder, so it can write make_row(7), make_row(8, term=...)."""
    return build_row


@pytest.fixture()
def db_rows():
    """Fresh copies of the three standard records the database tests use."""
    return [dict(row) for row in DB_ROWS]


@pytest.fixture(scope="session")
def database_url():
    """The test database URL (must end in _test); the table is created if missing."""
    url = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL", "")
    if not url.rstrip("/").endswith("_test"):
        pytest.fail(
            "Database tests need a database whose name ends in _test. Run:\n"
            '  export TEST_DATABASE_URL="postgresql://postgres:PASSWORD@localhost:5432/gradcafe_test"'
        )
    ensure_table(url)
    return url


@pytest.fixture()
def clean_db(database_url):
    """Empty the applicants table before the test, and again after it."""
    with psycopg.connect(database_url) as conn:
        conn.execute("TRUNCATE applicants")
    yield database_url
    with psycopg.connect(database_url) as conn:
        conn.execute("TRUNCATE applicants")


@pytest.fixture()
def db_app(clean_db):
    """The app wired to the empty test database; its scraper returns DB_ROWS."""
    app = create_app(scraper=lambda: [dict(row) for row in DB_ROWS],
                     database_url=clean_db, run_in_background=False)
    app.config["TESTING"] = True
    yield app


@pytest.fixture()
def db_client(db_app):
    """A test browser for db_app."""
    return db_app.test_client()