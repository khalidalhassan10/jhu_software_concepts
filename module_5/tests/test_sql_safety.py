"""Tests for the SQL-injection and LIMIT defences (Module 5)."""
import psycopg
import pytest

from src import query_data
from src.db_config import clamp_limit
from src.flask_app import create_app
from src.load_data import count_rows, insert_rows


@pytest.mark.db
@pytest.mark.parametrize("requested, expected", [
    (None, 20),
    ("abc", 20),
    ("5; DROP TABLE applicants", 20),
    ("7.5", 20),
    ("0", 1),
    ("-3", 1),
    ("50", 50),
    (100, 100),
    ("100000", 100),
])
def test_clamp_limit_always_returns_1_to_100(requested, expected):
    assert clamp_limit(requested) == expected


@pytest.mark.db
def test_build_search_keeps_values_out_of_the_sql(clean_db):
    statement, params = query_data.build_search({"term": "Fall 2026"}, sort="gpa", limit="5")

    with psycopg.connect(clean_db) as conn:
        text = statement.as_string(conn)

    assert "Fall 2026" not in text
    assert '"term" ILIKE %s' in text
    assert 'ORDER BY "gpa" LIMIT %s' in text
    assert params == ["%Fall 2026%", 5]


@pytest.mark.db
@pytest.mark.parametrize("typed, pattern", [
    ("Fall 2026", "%Fall 2026%"),
    ("50%", "%50\\%%"),
    ("a_b", "%a\\_b%"),
    ("x\\y", "%x\\\\y%"),
])
def test_contains_pattern_escapes_wildcards(typed, pattern):
    assert query_data.contains_pattern(typed) == pattern


@pytest.mark.db
def test_search_filters_sorts_and_limits(clean_db, make_row):
    insert_rows([
        make_row(1, GPA="3.90"),
        make_row(2, GPA="3.10"),
        make_row(3, GPA="3.50", term="Fall 2025"),
        make_row(4, GPA="3.70", date_added=""),
    ], clean_db)

    rows = query_data.search_applicants(
        {"term": "fall 2026"}, sort="gpa", limit=2, database_url=clean_db
    )
    assert [row["p_id"] for row in rows] == [2, 4]
    assert list(rows[0]) == list(query_data.RESULT_COLUMNS)
    assert rows[0]["date_added"] == "2026-09-12"
    assert rows[1]["date_added"] is None

    everything = query_data.search_applicants({}, sort="not_a_column", database_url=clean_db)
    assert [row["p_id"] for row in everything] == [1, 2, 3, 4]


@pytest.mark.db
@pytest.mark.web
def test_search_endpoint_returns_matching_rows(db_client, clean_db, make_row):
    insert_rows([make_row(1, GPA="3.90"), make_row(2, GPA="3.10")], clean_db)

    response = db_client.get("/api/applicants?term=Fall 2026&sort=gpa&limit=1")

    assert response.status_code == 200
    body = response.get_json()
    assert body["ok"] is True
    assert body["limit"] == 1
    assert body["count"] == 1
    assert body["results"][0]["p_id"] == 2


@pytest.mark.web
def test_search_endpoint_answers_500_when_the_database_is_down():
    app = create_app(database_url="postgresql://nobody@127.0.0.1:1/missing_test",
                     run_in_background=False)

    response = app.test_client().get("/api/applicants?term=Fall 2026")

    assert response.status_code == 500
    assert response.get_json() == {"ok": False, "error": "Could not run the search."}


ATTACKS = [
    "' OR 1=1 --",
    "x'; DROP TABLE applicants; --",
    "Fall 2026' UNION SELECT usename FROM pg_user --",
    "%",
    "_",
]


@pytest.mark.db
def test_normal_search_still_works(searchable_db):
    rows = query_data.search_applicants({"term": "Fall 2025"}, limit=100, database_url=searchable_db)

    assert len(rows) == 52
    assert all(row["term"] == "Fall 2025" for row in rows)


@pytest.mark.db
@pytest.mark.parametrize("field", ["term", "program"])
@pytest.mark.parametrize("attack", ATTACKS)
def test_search_treats_attacks_as_plain_text(searchable_db, field, attack):
    rows = query_data.search_applicants({field: attack}, database_url=searchable_db)

    assert rows == []
    assert count_rows(searchable_db) == 105


@pytest.mark.db
def test_sort_attack_falls_back_to_p_id(searchable_db):
    rows = query_data.search_applicants(
        {}, sort="gpa; DROP TABLE applicants", limit=5, database_url=searchable_db
    )

    assert [row["p_id"] for row in rows] == [1, 2, 3, 4, 5]
    assert count_rows(searchable_db) == 105


@pytest.mark.db
@pytest.mark.parametrize("requested, expected", [
    ("100000", 100),
    ("abc", 20),
    ("0", 1),
    (None, 20),
    ("5; DELETE FROM applicants", 20),
])
def test_search_limit_is_always_clamped(searchable_db, requested, expected):
    rows = query_data.search_applicants({}, limit=requested, database_url=searchable_db)

    assert len(rows) == expected
    assert count_rows(searchable_db) == 105


@pytest.mark.db
@pytest.mark.web
@pytest.mark.parametrize("attack", ATTACKS)
def test_search_endpoint_treats_attacks_as_plain_text(searchable_db, db_client, attack):
    response = db_client.get("/api/applicants", query_string={"term": attack})

    assert response.status_code == 200
    assert response.get_json()["count"] == 0
    assert count_rows(searchable_db) == 105


@pytest.mark.db
@pytest.mark.web
def test_search_endpoint_caps_the_limit(searchable_db, db_client):
    body = db_client.get("/api/applicants", query_string={"limit": "100000"}).get_json()

    assert body["limit"] == 100
    assert body["count"] == 100
