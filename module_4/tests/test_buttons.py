"""Tests for the Pull Data and Update Analysis buttons, and busy gating (assignment question 2).

All fakes come from conftest.py: no database, no internet, no sleep().
"""
import threading

import pytest

from src.flask_app import create_app


@pytest.mark.buttons
def test_pull_data_returns_ok_and_triggers_loader(client, fake_scraper, recording_loader):
    scraped = fake_scraper()

    response = client.post("/pull-data")

    assert response.status_code == 200
    assert response.get_json() == {"ok": True, "inserted": len(scraped)}
    assert recording_loader.calls == [scraped]


@pytest.mark.buttons
def test_update_analysis_returns_200_when_not_busy(client, fake_query):
    response = client.post("/update-analysis")

    assert response.status_code == 200
    assert response.get_json() == {"ok": True}
    assert fake_query.calls == 1


@pytest.mark.buttons
def test_update_analysis_is_gated_while_busy(app, client, fake_query):
    app.config["PULL_STATE"].busy = True

    response = client.post("/update-analysis")

    assert response.status_code == 409
    assert response.get_json() == {"busy": True}
    assert fake_query.calls == 0


@pytest.mark.buttons
def test_pull_data_is_gated_while_busy(app, client, recording_loader):
    app.config["PULL_STATE"].busy = True

    response = client.post("/pull-data")

    assert response.status_code == 409
    assert response.get_json() == {"busy": True}
    assert recording_loader.calls == []


@pytest.mark.buttons
def test_page_shows_busy_state(app, client):
    app.config["PULL_STATE"].busy = True

    html = client.get("/analysis").get_data(as_text=True)

    assert 'data-testid="busy-notice"' in html
    assert "disabled" in html


@pytest.mark.buttons
def test_pull_data_reports_loader_failure(fake_scraper, fake_query):
    def broken_loader(rows):
        raise RuntimeError("database is down")

    app = create_app(scraper=fake_scraper, loader=broken_loader, query=fake_query,
                     database_url="postgresql://unused", run_in_background=False)
    client = app.test_client()

    response = client.post("/pull-data")

    assert response.status_code == 500
    assert response.get_json() == {"ok": False, "error": "database is down"}
    assert app.config["PULL_STATE"].busy is False
    assert "Last pull failed: database is down" in client.get("/analysis").get_data(as_text=True)


@pytest.mark.buttons
def test_update_analysis_reports_query_failure():
    def broken_query():
        raise RuntimeError("database is down")

    app = create_app(scraper=lambda: [], loader=lambda rows: 0, query=broken_query,
                     database_url="postgresql://unused", run_in_background=False)

    response = app.test_client().post("/update-analysis")

    assert response.status_code == 500
    assert response.get_json() == {"ok": False, "error": "database is down"}


@pytest.mark.buttons
def test_pull_data_runs_in_background_and_returns_202(fake_scraper, fake_query):
    finished = threading.Event()

    def loader(rows):
        finished.set()
        return len(rows)

    app = create_app(scraper=fake_scraper, loader=loader, query=fake_query,
                     database_url="postgresql://unused", run_in_background=True)

    response = app.test_client().post("/pull-data")

    assert response.status_code == 202
    assert response.get_json() == {"ok": True}
    assert finished.wait(timeout=5)