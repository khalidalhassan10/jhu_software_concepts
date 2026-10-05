"""Tests for the Flask app factory and the Analysis page (assignment question 1)."""
import pytest
from bs4 import BeautifulSoup
from flask import Flask

from src.flask_app import create_app


@pytest.mark.web
def test_create_app_has_required_routes():
    app = create_app(query=lambda: {}, database_url="postgresql://unused")

    assert isinstance(app, Flask)

    routes = {rule.rule for rule in app.url_map.iter_rules()}
    assert {"/analysis", "/pull-data", "/update-analysis"} <= routes


@pytest.mark.web
@pytest.mark.parametrize("page_name, expected_result", [
    ("/analysis", 200),
    ("/", 302),
])
def test_page_load(page_name, expected_result, client):
    response = client.get(page_name)
    assert response.status_code == expected_result


@pytest.mark.web
def test_page_has_both_buttons(client):
    soup = BeautifulSoup(client.get("/analysis").data, "html.parser")

    pull = soup.find(attrs={"data-testid": "pull-data-btn"})
    update = soup.find(attrs={"data-testid": "update-analysis-btn"})

    assert pull is not None
    assert "Pull Data" in pull.get_text()
    assert update is not None
    assert "Update Analysis" in update.get_text()


@pytest.mark.web
def test_page_has_analysis_and_answer_text(client):
    text = BeautifulSoup(client.get("/analysis").data, "html.parser").get_text()

    assert "Analysis" in text
    assert "Answer:" in text
