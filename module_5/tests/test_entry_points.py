"""Tests that run each module the way a person does from the terminal (python -m src.<name>).

runpy executes the module as "__main__", so the lines under ``if __name__ == "__main__":`` run
too. Nothing reaches the internet: scrape.py's network functions are replaced with monkeypatch,
and Flask's run() is replaced so no server starts.
"""
import json
import runpy
import sys

import flask
import pytest

from src import load_data, scrape

pytestmark = pytest.mark.filterwarnings("ignore:.*found in sys.modules")

ONE_ENTRY_PAGE = (
    "<table><tr><td>MIT</td><td><span>Computer Science</span><span>PhD</span></td>"
    "<td>Sep 12, 2026</td><td>Accepted on Sep 11</td>"
    '<td><a href="/result/51">See more</a></td></tr></table>'
)


@pytest.mark.db
def test_load_data_as_a_script(clean_db, db_rows, tmp_path, monkeypatch, capsys):
    data_file = tmp_path / "rows.json"
    data_file.write_text(json.dumps(db_rows), encoding="utf-8")
    monkeypatch.setenv("DATABASE_URL", clean_db)
    monkeypatch.setattr(sys, "argv", ["load_data", str(data_file)])

    runpy.run_module("src.load_data", run_name="__main__")

    assert "Inserted 3 new applicants." in capsys.readouterr().out
    assert load_data.count_rows(clean_db) == 3


@pytest.mark.db
def test_query_data_as_a_script(clean_db, monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_URL", clean_db)

    runpy.run_module("src.query_data", run_name="__main__")

    assert "Fall 2026 applicant count: 0" in capsys.readouterr().out


@pytest.mark.buttons
@pytest.mark.db
def test_pull_data_as_a_script(clean_db, monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_URL", clean_db)
    monkeypatch.setattr(scrape, "check_robots", lambda: True)
    monkeypatch.setattr(scrape, "fetch_with_urllib3", lambda url: (200, ONE_ENTRY_PAGE))

    runpy.run_module("src.pull_data", run_name="__main__")

    assert "Pull complete: 1 new entries" in capsys.readouterr().out
    assert load_data.count_rows(clean_db) == 1


@pytest.mark.buttons
@pytest.mark.db
def test_pull_data_script_exits_with_an_error(clean_db, monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_URL", clean_db)
    monkeypatch.setattr(scrape, "check_robots", lambda: False)

    with pytest.raises(SystemExit) as stopped:
        runpy.run_module("src.pull_data", run_name="__main__")

    assert stopped.value.code == 1
    assert "Pull failed" in capsys.readouterr().err


@pytest.mark.web
def test_flask_app_as_a_script(monkeypatch):
    started = []
    monkeypatch.setenv("DATABASE_URL", "postgresql://unused")
    monkeypatch.setattr(flask.Flask, "run", lambda self, **options: started.append(options))

    runpy.run_module("src.flask_app", run_name="__main__")

    assert started == [{"debug": False, "use_reloader": False}]
