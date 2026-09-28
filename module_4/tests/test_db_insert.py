"""Tests for database writes, uniqueness and the query function (assignment question 4).

These use the REAL test database (gradcafe_test) through the fixtures in conftest.py:
only the scraper is fake. Every test starts with an empty applicants table.
"""
import json

import psycopg
import pytest

from src import load_data
from src.models import create_session_factory
from src.orm_queries import run_analyses

REQUIRED_FIELDS = ("p_id", "program", "url", "status", "term", "date_added")


def count_rows(database_url):
    return load_data.count_rows(database_url)


@pytest.mark.db
def test_pull_inserts_rows_with_required_fields(db_client, clean_db, db_rows):
    assert count_rows(clean_db) == 0

    response = db_client.post("/pull-data")

    assert response.status_code == 200
    assert response.get_json() == {"ok": True, "inserted": len(db_rows)}
    with psycopg.connect(clean_db) as conn:
        rows = conn.execute(
            f"SELECT {', '.join(REQUIRED_FIELDS)} FROM applicants ORDER BY p_id"
        ).fetchall()
    assert len(rows) == len(db_rows)
    assert all(value is not None for row in rows for value in row)
    assert [row[0] for row in rows] == [1, 2, 3]


@pytest.mark.db
def test_pull_stores_converted_values(db_client, clean_db):
    db_client.post("/pull-data")

    with psycopg.connect(clean_db) as conn:
        gpa_1, date_1 = conn.execute("SELECT gpa, date_added FROM applicants WHERE p_id = 1").fetchone()
        gpa_3 = conn.execute("SELECT gpa FROM applicants WHERE p_id = 3").fetchone()[0]

    assert gpa_1 == 3.8
    assert str(date_1) == "2026-09-12"
    assert gpa_3 is None


@pytest.mark.db
def test_duplicate_pull_does_not_duplicate_rows(db_client, clean_db, db_rows):
    first = db_client.post("/pull-data").get_json()
    second = db_client.post("/pull-data").get_json()

    assert first["inserted"] == len(db_rows)
    assert second["inserted"] == 0
    assert count_rows(clean_db) == len(db_rows)


@pytest.mark.db
def test_duplicate_inside_one_batch_is_stored_once(clean_db, make_row):
    inserted = load_data.insert_rows([make_row(7), make_row(7)], clean_db)

    assert inserted == 1
    assert count_rows(clean_db) == 1


EXPECTED_SCHEMA = {
    "p_id": "integer", "program": "text", "comments": "text", "date_added": "date",
    "url": "text", "status": "text", "term": "text", "us_or_international": "text",
    "gpa": "double precision", "gre": "double precision", "gre_v": "double precision",
    "gre_aw": "double precision", "degree": "text",
    "llm_generated_program": "text", "llm_generated_university": "text",
}


@pytest.mark.db
def test_table_has_the_module_3_schema(clean_db):
    with psycopg.connect(clean_db) as conn:
        columns = dict(conn.execute(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name = 'applicants'"
        ).fetchall())

    assert columns == EXPECTED_SCHEMA


@pytest.mark.db
def test_query_function_returns_expected_keys(db_client, clean_db):
    db_client.post("/pull-data")

    with create_session_factory(clean_db)() as session:
        result = run_analyses(session)

    assert isinstance(result, dict)
    assert set(result) == {"q1", "q2", "q3", "q4", "q5", "q6", "q7",
                           "q8", "q9", "q10", "q10_total", "q11"}
    assert result["q1"] == 2
    assert round(result["q2"], 2) == 66.67


@pytest.mark.db
def test_failed_batch_leaves_no_partial_writes(clean_db, make_row):
    good = make_row(10)
    too_big = make_row(99999999999)

    with pytest.raises(psycopg.errors.NumericValueOutOfRange):
        load_data.insert_rows([good, too_big], clean_db)

    assert count_rows(clean_db) == 0


@pytest.mark.db
def test_malformed_records_are_skipped(clean_db, make_row):
    records = [None, 5, {}, {"url": ""}, {"url": "https://www.thegradcafe.com/result/abc"}, make_row(11)]

    assert load_data.insert_rows(records, clean_db) == 1
    assert count_rows(clean_db) == 1


@pytest.mark.db
@pytest.mark.parametrize("converter, raw, expected", [
    (load_data.to_text, "  Fall 2026 ", "Fall 2026"),
    (load_data.to_text, "   ", None),
    (load_data.to_text, None, None),
    (load_data.to_float, "3.80", 3.8),
    (load_data.to_float, "", None),
    (load_data.to_float, "abc", None),
    (load_data.to_float, "nan", None),
    (load_data.result_id, "https://www.thegradcafe.com/result/1020482", 1020482),
    (load_data.result_id, "https://www.thegradcafe.com/result/1020482/", 1020482),
    (load_data.result_id, None, None),
    (load_data.result_id, "https://x/result/abc", None),
])
def test_converters(converter, raw, expected):
    assert converter(raw) == expected


@pytest.mark.db
@pytest.mark.parametrize("raw, expected", [
    ("Sep 12, 2026", "2026-09-12"),
    ("", None),
    ("12/09/2026", None),
])
def test_to_date(raw, expected):
    result = load_data.to_date(raw)
    assert (str(result) if result else None) == expected


@pytest.mark.db
def test_load_file_and_main(clean_db, tmp_path, capsys, monkeypatch, db_rows):
    data_file = tmp_path / "rows.json"
    data_file.write_text(json.dumps(db_rows), encoding="utf-8")

    assert load_data.load_file(data_file, clean_db) == (3, 3)

    monkeypatch.setenv("DATABASE_URL", clean_db)
    load_data.main([str(data_file)])
    printed = capsys.readouterr().out

    assert "Read 3 records" in printed
    assert "Inserted 0 new applicants." in printed
    assert "Applicants stored in PostgreSQL: 3" in printed