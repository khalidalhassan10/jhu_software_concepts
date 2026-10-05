"""Tests for the helper methods every model gets from Base (models.py)."""
import pytest

from src.models import Applicant


@pytest.mark.db
def test_model_rows_convert_to_dictionaries():
    row = Applicant(p_id=7, program="Physics, MIT")

    assert row.column_names()[:3] == ["p_id", "program", "comments"]
    assert row.as_dict()["program"] == "Physics, MIT"
