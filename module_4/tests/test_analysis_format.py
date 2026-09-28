"""Tests for analysis labels and number formatting (assignment question 3).

Uses the fake app from conftest.py (SAMPLE_RESULT: no database).
"""
import re

import pytest
from bs4 import BeautifulSoup

from src.flask_app import fmt_avg, fmt_count, fmt_pct, format_analysis

ANY_PERCENT = re.compile(r"\d+(?:\.\d+)?%")
TWO_DECIMALS = re.compile(r"\d+\.\d{2}%")


def answers_on_page(client):
    """Return the answer text of every analysis card, in page order."""
    soup = BeautifulSoup(client.get("/analysis").data, "html.parser")
    cards = soup.find_all(attrs={"data-testid": "analysis-item"})
    return [card.find(class_="value").get_text(strip=True) for card in cards]


@pytest.mark.analysis
def test_every_answer_is_labelled(client):
    answers = answers_on_page(client)

    assert len(answers) == 18
    assert all(text.startswith("Answer:") for text in answers)


@pytest.mark.analysis
def test_every_percentage_has_two_decimals(client):
    page_text = BeautifulSoup(client.get("/analysis").data, "html.parser").get_text()

    found = ANY_PERCENT.findall(page_text)

    assert found
    assert all(TWO_DECIMALS.fullmatch(p) for p in found)


@pytest.mark.analysis
def test_percentages_are_rounded_correctly(client):
    answers = answers_on_page(client)

    assert "Answer: 50.09%" in answers
    assert "Answer: 39.28%" in answers
    assert "Answer: 569 of 1,679 (33.89%)" in answers


@pytest.mark.analysis
@pytest.mark.parametrize("formatter, value, expected", [
    (fmt_pct, 39.284, "39.28%"),
    (fmt_pct, 47.5, "47.50%"),
    (fmt_pct, 100, "100.00%"),
    (fmt_pct, None, "n/a"),
    (fmt_avg, 3.7712, "3.77"),
    (fmt_avg, None, "n/a"),
    (fmt_count, 19290, "19,290"),
    (fmt_count, None, "n/a"),
])
def test_formatters(formatter, value, expected):
    assert formatter(value) == expected


EMPTY_RESULT = {
    "q1": 0, "q2": None, "q3": (None, None, None, None),
    "q4": None, "q5": None, "q6": None, "q7": 0, "q8": 0, "q9": 0,
    "q10_total": 0, "q10": [], "q11": (0, None, 0, None),
}


@pytest.mark.analysis
def test_empty_database_shows_n_a():
    items = format_analysis(EMPTY_RESULT)
    answers = dict(items)

    assert len(items) == 18
    assert all(answer.startswith("Answer:") for _, answer in items)
    assert answers["Q2. Percent international"] == "Answer: n/a"
    assert answers["Q10. Fall 2026 CS entries that are Masters"] == "Answer: n/a"
    assert answers["Q11. GPA difference (accepted minus rejected)"] == "Answer: n/a"