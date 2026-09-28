"""End-to-end tests: pull -> update -> render, against the REAL test database (assignment question 5).

Only the scraper is fake; the loader, the ORM query and the page are the real ones.
"""
import re

import pytest
from bs4 import BeautifulSoup

from src import load_data
from src.flask_app import create_app

TWO_DECIMALS = re.compile(r"\d+\.\d{2}%")
ANY_PERCENT = re.compile(r"\d+(?:\.\d+)?%")


def answers(client):
    """Open /analysis and return a dictionary of question label -> answer text."""
    soup = BeautifulSoup(client.get("/analysis").data, "html.parser")
    return {
        card.find(class_="label").get_text(strip=True): card.find(class_="value").get_text(strip=True)
        for card in soup.find_all(attrs={"data-testid": "analysis-item"})
    }


@pytest.mark.integration
def test_pull_update_render(clean_db, make_row):
    records = [
        make_row(11),
        make_row(12, **{"US/International": "American"}),
        make_row(13, term="Fall 2025", status="Rejected on Aug 01"),
    ]
    app = create_app(scraper=lambda: records, database_url=clean_db, run_in_background=False)
    client = app.test_client()

    before = answers(client)
    assert before["Q1. Fall 2026 applicant count"] == "Answer: 0"

    response = client.post("/pull-data")
    assert response.status_code == 200
    assert response.get_json() == {"ok": True, "inserted": 3}
    assert load_data.count_rows(clean_db) == 3

    assert answers(client)["Q1. Fall 2026 applicant count"] == "Answer: 0"

    assert client.post("/update-analysis").status_code == 200

    after = answers(client)
    assert after["Q1. Fall 2026 applicant count"] == "Answer: 2"
    assert after["Q2. Percent international"] == "Answer: 66.67%"
    assert after["Q5. Fall 2025 acceptance percentage"] == "Answer: 0.00%"
    percentages = [p for text in after.values() for p in ANY_PERCENT.findall(text)]
    assert percentages and all(TWO_DECIMALS.fullmatch(p) for p in percentages)


@pytest.mark.integration
def test_overlapping_pulls_keep_one_row_per_p_id(clean_db, make_row):
    batches = [
        [make_row(21), make_row(22)],
        [make_row(22), make_row(23)],
    ]
    app = create_app(scraper=lambda: batches.pop(0),
                     database_url=clean_db, run_in_background=False)
    client = app.test_client()

    first = client.post("/pull-data").get_json()
    second = client.post("/pull-data").get_json()

    assert first["inserted"] == 2
    assert second["inserted"] == 1
    assert load_data.count_rows(clean_db) == 3

    client.post("/update-analysis")
    assert answers(client)["Q1. Fall 2026 applicant count"] == "Answer: 3"