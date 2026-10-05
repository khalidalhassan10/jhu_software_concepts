"""Answer the Module 3 questions with raw SQL through psycopg, and print the results.

Import-safe: nothing runs on import. Run ``python -m src.query_data``.
"""


import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from src.db_config import clamp_limit, get_database_url
from src.load_data import TABLE


Q1_TERM_COUNT = sql.SQL(
    "SELECT COUNT(term) FROM {table} WHERE term ILIKE %s LIMIT %s"
).format(table=TABLE)

Q2_PERCENT_INTERNATIONAL = sql.SQL("""
    SELECT
        100.0 * COUNT(*) FILTER (
            WHERE us_or_international ILIKE %s
        )
        / NULLIF(COUNT(*), 0)
    FROM {table}
    WHERE us_or_international IS NOT NULL
      AND TRIM(us_or_international) <> ''
    LIMIT %s
""").format(table=TABLE)

Q4_AMERICAN_GPA = sql.SQL("""
    SELECT AVG(gpa) FROM {table}
    WHERE us_or_international ILIKE %s
      AND term ILIKE %s
    LIMIT %s
""").format(table=TABLE)

Q5_ACCEPTANCE_PERCENT = sql.SQL("""
    SELECT
        100.0 * COUNT(*) FILTER (
            WHERE status ILIKE %s
        )
        / NULLIF(COUNT(*), 0)
    FROM {table}
    WHERE term ILIKE %s
    LIMIT %s
""").format(table=TABLE)

Q6_ACCEPTED_GPA = sql.SQL("""
    SELECT AVG(gpa) FROM {table}
    WHERE term ILIKE %s
      AND status ILIKE %s
    LIMIT %s
""").format(table=TABLE)

Q7_JHU_CS_MASTERS = sql.SQL("""
    SELECT COUNT(*)
    FROM {table}
    WHERE (program ILIKE %s
      OR program ILIKE %s)
      AND program ILIKE %s
      AND degree ILIKE %s
    LIMIT %s
""").format(table=TABLE)

Q8_ORIGINAL_FIELDS = sql.SQL("""
    SELECT COUNT(*)
    FROM {table}
    WHERE (program ILIKE %s
      OR program ILIKE %s
      OR program ILIKE %s
      OR program ILIKE %s
      OR program ILIKE %s)
      AND program ILIKE %s
      AND degree ILIKE %s
      AND term ILIKE %s
      AND status ILIKE %s
    LIMIT %s
""").format(table=TABLE)

Q9_LLM_FIELDS = sql.SQL("""
    SELECT COUNT(*)
    FROM {table}
    WHERE (llm_generated_university ILIKE %s
      OR llm_generated_university ILIKE %s
      OR llm_generated_university ILIKE %s
      OR llm_generated_university ILIKE %s
      OR llm_generated_university ILIKE %s)
      AND llm_generated_program ILIKE %s
      AND degree ILIKE %s
      AND term ILIKE %s
      AND status ILIKE %s
    LIMIT %s
""").format(table=TABLE)

Q10_MASTERS_VS_PHD = sql.SQL("""
    SELECT
        COUNT(*) FILTER (WHERE degree ILIKE %s) AS masters_count,
        COUNT(*) FILTER (WHERE degree ILIKE %s) AS phd_count,
        COUNT(*) AS total_count,
        100.0 * COUNT(*) FILTER (WHERE degree ILIKE %s)
            / NULLIF(COUNT(*), 0) AS masters_percentage,
        100.0 * COUNT(*) FILTER (WHERE degree ILIKE %s)
            / NULLIF(COUNT(*), 0) AS phd_percentage
    FROM {table}
    WHERE term ILIKE %s
      AND program ILIKE %s
    LIMIT %s
""").format(table=TABLE)

Q11_ACCEPTED_VS_REJECTED_GPA = sql.SQL("""
    WITH averages AS (
        SELECT
            COUNT(gpa) FILTER (WHERE status ILIKE %s) AS accepted_count,
            AVG(gpa) FILTER (WHERE status ILIKE %s) AS accepted_avg,
            COUNT(gpa) FILTER (WHERE status ILIKE %s) AS rejected_count,
            AVG(gpa) FILTER (WHERE status ILIKE %s) AS rejected_avg
        FROM {table}
        WHERE term ILIKE %s
          AND program ILIKE %s
          AND degree ILIKE %s
    )
    SELECT accepted_count, accepted_avg, rejected_count, rejected_avg,
           accepted_avg - rejected_avg
    FROM averages
    LIMIT %s
""").format(table=TABLE)

SEARCH_FIELDS = ("term", "degree", "status", "program", "us_or_international")
SORTABLE_COLUMNS = ("p_id", "date_added", "gpa", "gre", "term", "program")
RESULT_COLUMNS = (
    "p_id", "program", "term", "degree", "status", "us_or_international", "gpa", "date_added",
)


def fmt(value, spec=".2f", suffix=""):
    """Format a number for printing; ``None`` (no data) becomes ``"n/a"``.

    :param value: a number, or ``None``.
    :param spec: the format spec, e.g. ``".2f"`` or ``"+.2f"``.
    :param suffix: text after the number, e.g. ``"%"``.
    :returns: the formatted text.
    """
    if value is None:
        return "n/a"
    return f"{value:{spec}}{suffix}"


def average_of(column):
    """Build ``SELECT AVG(column) FROM applicants LIMIT %s`` for one column, safely.

    :param column: the column to average, e.g. ``"gpa"``.
    :returns: the composed statement.
    """
    return sql.SQL("SELECT AVG({column}) FROM {table} LIMIT %s").format(
        column=sql.Identifier(column), table=TABLE
    )


def main(database_url=None):
    """Run the eleven analysis questions in SQL and print each answer.

    :param database_url: optional URL overriding DATABASE_URL (tests pass their test database).
    """
    with psycopg.connect(get_database_url(database_url)) as connection:
        with connection.cursor() as cur:

            cur.execute(Q1_TERM_COUNT, ("Fall 2026", 1))
            print(f"Fall 2026 applicant count: {cur.fetchone()[0]}")

            cur.execute(Q2_PERCENT_INTERNATIONAL, ("International", 1))
            print(f"Percent international: {fmt(cur.fetchone()[0], suffix='%')}")

            cur.execute(average_of("gpa"), (1,))
            print(f"Average GPA: {fmt(cur.fetchone()[0])}")

            cur.execute(average_of("gre"), (1,))
            print(f"Average GRE Quantitative: {fmt(cur.fetchone()[0])}")

            cur.execute(average_of("gre_v"), (1,))
            print(f"Average GRE Verbal: {fmt(cur.fetchone()[0])}")

            cur.execute(average_of("gre_aw"), (1,))
            print(f"Average GRE Analytical Writing: {fmt(cur.fetchone()[0])}")

            cur.execute(Q4_AMERICAN_GPA, ("American", "Fall 2026", 1))
            print(f"Average GPA of Americans for Fall 2026: {fmt(cur.fetchone()[0])}")

            cur.execute(Q5_ACCEPTANCE_PERCENT, ("Accepted%", "Fall 2025", 1))
            print(f"Fall 2025 acceptance percentage: {fmt(cur.fetchone()[0], suffix='%')}")

            cur.execute(Q6_ACCEPTED_GPA, ("FALL 2026", "Accepted%", 1))
            print(f"Average GPA of accepted applicants in Fall 2026: {fmt(cur.fetchone()[0])}")

            cur.execute(
                Q7_JHU_CS_MASTERS,
                ("%Johns Hopkins%", "%JHU%", "%Computer Science%", "Masters", 1),
            )
            print(
                "Applicants applied to Johns Hopkins University for a master's degree "
                f"in Computer Science: {cur.fetchone()[0]}"
            )

            cur.execute(Q8_ORIGINAL_FIELDS, (
                "%Georgetown University%", "%Massachusetts Institute of Technology%",
                "%, MIT%", "%Stanford University%", "%Carnegie Mellon University%",
                "%Computer Science%", "PhD", "FALL 2026", "Accepted%", 1,
            ))
            q8_count = cur.fetchone()[0]
            print(
                "Accepted PhD in Computer Science applicants in Fall 2026 in "
                f"Georgetown, MIT, Stanford and CMU is: {q8_count}"
            )

            cur.execute(Q9_LLM_FIELDS, (
                "%Georgetown University%", "%Massachusetts Institute of Technology%",
                "MIT", "%Stanford University%", "%Carnegie Mellon University%",
                "%Computer Science%", "PhD", "FALL 2026", "Accepted%", 1,
            ))
            q9_count = cur.fetchone()[0]
            print(f"Original-field count: {q8_count}")
            print(f"LLM-field count: {q9_count}")
            print(f"Difference: {q9_count - q8_count:+d}")

            cur.execute(Q10_MASTERS_VS_PHD, (
                "Masters", "PhD", "Masters", "PhD", "Fall 2026", "%Computer Science%", 1,
            ))
            masters_count, phd_count, total_count, masters_pct, phd_pct = cur.fetchone()
            print(f"Computer Science entries in Fall 2026: {total_count}")
            print(f"Masters: {masters_count} ({fmt(masters_pct, suffix='%')})")
            print(f"PhD: {phd_count} ({fmt(phd_pct, suffix='%')})")

            cur.execute(Q11_ACCEPTED_VS_REJECTED_GPA, (
                "Accepted%", "Accepted%", "Rejected%", "Rejected%",
                "Fall 2026", "%Computer Science%", "Masters", 1,
            ))
            accepted_count, accepted_avg, rejected_count, rejected_avg, difference = cur.fetchone()
            print(f"Accepted: {accepted_count} reported GPAs, average {fmt(accepted_avg)}")
            print(f"Rejected: {rejected_count} reported GPAs, average {fmt(rejected_avg)}")
            print(f"Average GPA difference: {fmt(difference, spec='+.2f')}")


def contains_pattern(value):
    """Turn user text into an ILIKE pattern that finds it anywhere, matching it literally.

    ``%``, ``_`` and ``\\`` typed by the user are escaped, so they match only themselves.

    :param value: the text the user typed.
    :returns: e.g. ``"%Fall 2026%"``.
    """
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def build_search(filters, sort="p_id", limit=None):
    """Build the search statement and its values, without running anything.

    :param filters: ``{field: text}`` typed by the user; only SEARCH_FIELDS are used.
    :param sort: the column to sort by; anything not in SORTABLE_COLUMNS becomes ``p_id``.
    :param limit: the requested number of rows, clamped to 1-100.
    :returns: ``(statement, params)``, ready for ``execute``.
    """
    conditions = []
    params = []
    for field in SEARCH_FIELDS:
        value = str(filters.get(field) or "").strip()
        if value:
            conditions.append(sql.SQL("{column} ILIKE %s").format(column=sql.Identifier(field)))
            params.append(contains_pattern(value))
    where = sql.SQL("")
    if conditions:
        where = sql.SQL(" WHERE {conditions}").format(conditions=sql.SQL(" AND ").join(conditions))
    sort_column = sort if sort in SORTABLE_COLUMNS else "p_id"
    statement = sql.SQL("SELECT {columns} FROM {table}{where} ORDER BY {sort} LIMIT %s").format(
        columns=sql.SQL(", ").join(sql.Identifier(name) for name in RESULT_COLUMNS),
        table=TABLE,
        where=where,
        sort=sql.Identifier(sort_column),
    )
    params.append(clamp_limit(limit))
    return statement, params


def search_applicants(filters, sort="p_id", limit=None, database_url=None):
    """Run the search that build_search builds, and return the matching rows.

    :param filters: ``{field: text}`` typed by the user.
    :param sort: the column to sort by.
    :param limit: the requested number of rows.
    :param database_url: optional URL overriding DATABASE_URL.
    :returns: a list of ``{column: value}`` dictionaries, dates as ``"YYYY-MM-DD"`` text.
    """
    statement, params = build_search(filters, sort, limit)
    with psycopg.connect(get_database_url(database_url), row_factory=dict_row) as conn:
        rows = conn.execute(statement, params).fetchall()
    for row in rows:
        if row["date_added"] is not None:
            row["date_added"] = row["date_added"].isoformat()
    return rows


if __name__ == "__main__":
    main()
