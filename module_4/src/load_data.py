"""Load Grad Café applicant records into the PostgreSQL ``applicants`` table.

Import-safe: importing this module does nothing. Loading happens only when a
function is called, or when you run ``python -m src.load_data FILE.json``.
"""


import json
import math
import sys
from datetime import datetime

import psycopg

from src.db_config import get_database_url


CREATE_TABLE = """
    CREATE TABLE IF NOT EXISTS applicants (
        p_id                     INTEGER PRIMARY KEY,
        program                  TEXT,
        comments                 TEXT,
        date_added               DATE,
        url                      TEXT,
        status                   TEXT,
        term                     TEXT,
        us_or_international      TEXT,
        gpa                      FLOAT,
        gre                      FLOAT,
        gre_v                    FLOAT,
        gre_aw                   FLOAT,
        degree                   TEXT,
        llm_generated_program    TEXT,
        llm_generated_university TEXT
    )
"""


INSERT = """
    INSERT INTO applicants (
        p_id, program, comments, date_added, url,
        status, term, us_or_international, gpa, gre,
        gre_v, gre_aw, degree, llm_generated_program, llm_generated_university
    ) VALUES (
        %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s
    ) ON CONFLICT (p_id) DO NOTHING
"""


def to_text(value):
    """Strip a value to text; empty or missing becomes ``None``.

    :param value: any value from the JSON file.
    :returns: the stripped text, or ``None``.
    """
    if value is None:
        return None
    return str(value).strip() or None


def to_float(value):
    """Convert text such as ``"3.80"`` to a float; anything unusable becomes ``None``.

    :param value: any value from the JSON file.
    :returns: a finite float, or ``None`` for blanks, text, ``nan`` and ``inf``.
    """
    value = to_text(value)
    if value is None:
        return None
    try:
        number = float(value)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def to_date(value):
    """Convert ``"Sep 12, 2026"`` to a date; blanks and bad formats become ``None``.

    :param value: any value from the JSON file.
    :returns: a ``datetime.date``, or ``None``.
    """
    value = to_text(value)
    if value is None:
        return None
    try:
        return datetime.strptime(value, "%b %d, %Y").date()
    except ValueError:
        return None


def result_id(url):
    """Take the p_id from the end of a Grad Café URL.

    :param url: e.g. ``"https://www.thegradcafe.com/result/1020482"``.
    :returns: ``1020482``, or ``None`` if the URL does not end in a number.
    """
    text = to_text(url)
    if text is None:
        return None
    last_part = text.rstrip("/").split("/")[-1]
    return int(last_part) if last_part.isdigit() else None


def row_to_values(applicant):
    """Map one scraped record to the 15 column values, in INSERT order.

    :param applicant: one dictionary from the JSON file.
    :returns: a 15-value tuple, or ``None`` if the record is malformed.
    """
    if not isinstance(applicant, dict):
        return None
    p_id = result_id(applicant.get("url"))
    if p_id is None:
        return None
    return (
        p_id,
        to_text(applicant.get("program")),
        to_text(applicant.get("comments")),
        to_date(applicant.get("date_added")),
        to_text(applicant.get("url")),
        to_text(applicant.get("status")),
        to_text(applicant.get("term")),
        to_text(applicant.get("US/International")),
        to_float(applicant.get("GPA")),
        to_float(applicant.get("GRE")),
        to_float(applicant.get("GRE V")),
        to_float(applicant.get("GRE AW")),
        to_text(applicant.get("Degree")),
        to_text(applicant.get("llm-generated-program")),
        to_text(applicant.get("llm-generated-university")),
    )


def ensure_table(database_url=None):
    """Create the ``applicants`` table if it does not exist yet.

    :param database_url: optional URL overriding DATABASE_URL.
    """
    with psycopg.connect(get_database_url(database_url)) as conn:
        conn.execute(CREATE_TABLE)


def insert_rows(rows, database_url=None):
    """Insert scraped records, skipping malformed ones and p_ids already stored.

    All rows go in one transaction: if one insert fails, none are kept.

    :param rows: a list of scraped record dictionaries.
    :param database_url: optional URL overriding DATABASE_URL.
    :returns: the number of rows actually inserted.
    """
    inserted = 0
    with psycopg.connect(get_database_url(database_url)) as conn:
        conn.execute(CREATE_TABLE)
        with conn.cursor() as cur:
            for applicant in rows:
                values = row_to_values(applicant)
                if values is None:
                    continue
                cur.execute(INSERT, values)
                inserted += cur.rowcount
    return inserted


def count_rows(database_url=None):
    """Return how many rows the ``applicants`` table holds.

    :param database_url: optional URL overriding DATABASE_URL.
    """
    with psycopg.connect(get_database_url(database_url)) as conn:
        return conn.execute("SELECT COUNT(*) FROM applicants").fetchone()[0]


def load_file(path, database_url=None):
    """Read a JSON file of records and insert them.

    :param path: the JSON file (a list of record dictionaries).
    :param database_url: optional URL overriding DATABASE_URL.
    :returns: ``(records_read, rows_inserted)``.
    """
    with open(path, encoding="utf-8") as file:
        rows = json.load(file)
    return len(rows), insert_rows(rows, database_url)


def main(argv=None):
    """Load a JSON file named on the command line and print a summary.

    :param argv: argument list (defaults to ``sys.argv[1:]``).
    """
    argv = sys.argv[1:] if argv is None else argv
    path = argv[0] if argv else "llm_extend_applicant_data.json"
    read, inserted = load_file(path)
    print(f"Read {read} records from {path}.")
    print(f"Inserted {inserted} new applicants.")
    print(f"Applicants stored in PostgreSQL: {count_rows()}")


if __name__ == "__main__":  # pragma: no cover
    main()
