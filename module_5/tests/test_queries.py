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
def test_database_url_is_built_from_the_five_db_variables(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_NAME", "gradcafe")
    monkeypatch.setenv("DB_USER", "gradcafe_app")
    monkeypatch.setenv("DB_PASSWORD", "p@ss/w:rd")

    assert db_config.get_database_url() == (
        "postgresql://gradcafe_app:p%40ss%2Fw%3Ard@localhost:5432/gradcafe"
    )


@pytest.mark.db
def test_missing_database_settings_raise_a_clear_error(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    for name in db_config.DB_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DB_HOST", "localhost")

    with pytest.raises(RuntimeError, match="missing: DB_PORT, DB_NAME, DB_USER, DB_PASSWORD"):
        db_config.get_database_url()


@pytest.mark.web
def test_page_explains_when_the_database_cannot_be_read():
    def broken_query():
        raise RuntimeError("connection refused")

    app = create_app(scraper=lambda: [], loader=lambda rows: 0, query=broken_query,
                     database_url="postgresql://unused", run_in_background=False)
    response = app.test_client().get("/analysis")

    page = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Could not read the database. Check that PostgreSQL is running." in page
    assert "connection refused" not in page
