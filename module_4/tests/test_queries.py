"""Tests for the query scripts (query_data.py, orm_queries.py), db_config.py and the page's
database-error message, run against the REAL test database."""
import runpy

import pytest

from src import db_config, query_data
from src.flask_app import create_app
from src.load_data import insert_rows
from src.models import create_session_factory
from src.orm_queries import display, run_analyses


@pytest.fixture()
def rows_with_a_rejection(db_rows, make_row):
    """The standard rows plus a rejected Fall 2026 CS master's entry with a GPA."""
    return db_rows + [make_row(4, status="Rejected on Sep 01", GPA="3.50")]


@pytest.mark.db
def test_query_data_prints_answers(clean_db, capsys, rows_with_a_rejection):
    insert_rows(rows_with_a_rejection, clean_db)

    query_data.main(clean_db)
    printed = capsys.readouterr().out

    assert "Fall 2026 applicant count: 3" in printed
    assert "Percent international: 75.00%" in printed
    assert "Average GPA difference: +0.30" in printed
    assert "Difference: +0" in printed


@pytest.mark.db
def test_query_data_on_an_empty_table_prints_n_a(clean_db, capsys):
    query_data.main(clean_db)
    printed = capsys.readouterr().out

    assert "Fall 2026 applicant count: 0" in printed
    assert "Percent international: n/a" in printed
    assert "Average GPA: n/a" in printed


@pytest.mark.analysis
@pytest.mark.db
def test_orm_display_prints_answers(clean_db, capsys, rows_with_a_rejection):
    insert_rows(rows_with_a_rejection, clean_db)

    with create_session_factory(clean_db)() as session:
        display(run_analyses(session))
    printed = capsys.readouterr().out

    assert "Percent international: 75.00%" in printed
    assert "Masters: 3 entries (100.00% of Fall 2026 CS entries)" in printed
    assert "Average GPA difference: +0.30" in printed


@pytest.mark.analysis
@pytest.mark.db
@pytest.mark.filterwarnings("ignore:'src.orm_queries' found in sys.modules")
def test_orm_script_on_an_empty_table(clean_db, capsys, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", clean_db)

    runpy.run_module("src.orm_queries", run_name="__main__")
    printed = capsys.readouterr().out

    assert "Percent international: no reported values" in printed
    assert "Average GPA difference: unavailable" in printed


@pytest.mark.db
def test_database_url_comes_from_argument_or_environment(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://from-environment")

    assert db_config.get_database_url() == "postgresql://from-environment"
    assert db_config.get_database_url("postgresql://passed-in") == "postgresql://passed-in"


@pytest.mark.db
def test_missing_database_url_raises_a_clear_error(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="DATABASE_URL is not set"):
        db_config.get_database_url()


@pytest.mark.web
def test_page_explains_when_the_database_cannot_be_read():
    def broken_query():
        raise RuntimeError("connection refused")

    app = create_app(scraper=lambda: [], loader=lambda rows: 0, query=broken_query,
                     database_url="postgresql://unused", run_in_background=False)
    response = app.test_client().get("/analysis")

    assert response.status_code == 200
    assert "Could not read the database: connection refused" in response.get_data(as_text=True)