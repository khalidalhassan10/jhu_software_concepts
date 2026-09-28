"""Answer the Module 3 questions with raw SQL through psycopg, and print the results.

Import-safe: nothing runs on import. Run ``python -m src.query_data``.
"""


import psycopg

from src.db_config import get_database_url


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


def main(database_url=None):
    """Run the eleven analysis questions in SQL and print each answer.

    :param database_url: optional URL overriding DATABASE_URL (tests pass their test database).
    """
    with psycopg.connect(get_database_url(database_url)) as connection:
        with connection.cursor() as cur:

            cur.execute("""
                SELECT COUNT(term) FROM applicants
                WHERE term ILIKE 'Fall 2026'
            """)
            print(f"Fall 2026 applicant count: {cur.fetchone()[0]}")


            cur.execute("""
                SELECT
                    100.0 * COUNT(*) FILTER (
                        WHERE us_or_international ILIKE 'International'
                    )
                    / NULLIF(COUNT(*), 0)
                FROM applicants
                WHERE us_or_international IS NOT NULL
                  AND TRIM(us_or_international) <> ''
            """)
            print(f"Percent international: {fmt(cur.fetchone()[0], suffix='%')}")


            cur.execute("SELECT avg(gpa) FROM applicants")
            print(f"Average GPA: {fmt(cur.fetchone()[0])}")


            cur.execute("SELECT avg(gre) FROM applicants")
            print(f"Average GRE Quantitative: {fmt(cur.fetchone()[0])}")


            cur.execute("SELECT avg(gre_v) FROM applicants")
            print(f"Average GRE Verbal: {fmt(cur.fetchone()[0])}")


            cur.execute("SELECT avg(gre_aw) FROM applicants")
            print(f"Average GRE Analytical Writing: {fmt(cur.fetchone()[0])}")


            cur.execute("""
                SELECT avg(gpa) FROM applicants
                WHERE us_or_international ILIKE 'American'
                AND term ILIKE 'Fall 2026'
            """)
            print(f"Average GPA of Americans for Fall 2026: {fmt(cur.fetchone()[0])}")


            cur.execute("""
                SELECT
                    100.0 * COUNT(*) FILTER (
                        WHERE status ILIKE 'Accepted%'
                    )
                    / NULLIF(COUNT(*), 0)
                FROM applicants
                WHERE term ILIKE 'Fall 2025'
            """)
            print(f"Fall 2025 acceptance percentage: {fmt(cur.fetchone()[0], suffix='%')}")


            cur.execute("""
                SELECT avg(gpa) FROM applicants
                WHERE term ILIKE 'FALL 2026'
                AND status ILIKE 'Accepted%'
            """)
            print(f"Average GPA of accepted applicants in Fall 2026: {fmt(cur.fetchone()[0])}")


            cur.execute("""
                SELECT COUNT(*)
                FROM applicants
                WHERE (program ILIKE '%Johns Hopkins%'
                OR program ILIKE '%JHU%' )
                AND program ILIKE '%Computer Science%'
                AND degree ILIKE 'Masters'
            """)
            print(
                "Applicants applied to Johns Hopkins University for a master's degree "
                f"in Computer Science: {cur.fetchone()[0]}"
            )


            cur.execute("""
                SELECT COUNT(*)
                FROM applicants
                WHERE (program ILIKE '%Georgetown University%'
                OR program ILIKE '%Massachusetts Institute of Technology%'
                OR program ILIKE '%, MIT%'
                OR program ILIKE '%Stanford University%'
                OR program ILIKE '%Carnegie Mellon University%')
                AND program ILIKE '%Computer Science%'
                AND degree ILIKE 'PhD'
                AND term ILIKE 'FALL 2026'
                AND status ILIKE 'Accepted%'
            """)
            q8_count = cur.fetchone()[0]
            print(
                "Accepted PhD in Computer Science applicants in Fall 2026 in "
                f"Georgetown, MIT, Stanford and CMU is: {q8_count}"
            )


            cur.execute("""
                SELECT COUNT(*)
                FROM applicants
                WHERE (llm_generated_university ILIKE '%Georgetown University%'
                OR llm_generated_university ILIKE '%Massachusetts Institute of Technology%'
                OR llm_generated_university ILIKE 'MIT'
                OR llm_generated_university ILIKE '%Stanford University%'
                OR llm_generated_university ILIKE '%Carnegie Mellon University%')
                AND llm_generated_program ILIKE '%Computer Science%'
                AND degree ILIKE 'PhD'
                AND term ILIKE 'FALL 2026'
                AND status ILIKE 'Accepted%'
            """)
            q9_count = cur.fetchone()[0]
            print(f"Original-field count: {q8_count}")
            print(f"LLM-field count: {q9_count}")
            cur.execute("SELECT %s::integer - %s::integer", (q9_count, q8_count))
            print(f"Difference: {cur.fetchone()[0]:+d}")


            cur.execute("""
                SELECT
                COUNT(*) FILTER (WHERE degree ILIKE 'Masters') AS masters_count,
                COUNT(*) FILTER (WHERE degree ILIKE 'PhD') AS phd_count,
                COUNT(*) AS total_count,
                100.0 * COUNT(*) FILTER (WHERE degree ILIKE 'Masters')
                / NULLIF(COUNT(*), 0) AS masters_percentage,
                100.0 * COUNT(*) FILTER (WHERE degree ILIKE 'PhD')
                / NULLIF(COUNT(*), 0) AS phd_percentage
                FROM applicants
                WHERE term ILIKE 'Fall 2026'
                AND program ILIKE '%Computer Science%'
            """)
            masters_count, phd_count, total_count, masters_pct, phd_pct = cur.fetchone()
            print(f"Computer Science entries in Fall 2026: {total_count}")
            print(f"Masters: {masters_count} ({fmt(masters_pct, suffix='%')})")
            print(f"PhD: {phd_count} ({fmt(phd_pct, suffix='%')})")


            cur.execute("""
                WITH averages AS (
                SELECT
                COUNT(gpa) FILTER (WHERE status ILIKE 'Accepted%') AS accepted_count,
                AVG(gpa) FILTER (WHERE status ILIKE 'Accepted%') AS accepted_avg,
                COUNT(gpa) FILTER (WHERE status ILIKE 'Rejected%') AS rejected_count,
                AVG(gpa) FILTER (WHERE status ILIKE 'Rejected%') AS rejected_avg
                FROM applicants
                WHERE term ILIKE 'Fall 2026'
                AND program ILIKE '%Computer Science%'
                AND degree ILIKE 'Masters'
                )
                SELECT accepted_count, accepted_avg, rejected_count, rejected_avg,
                       accepted_avg - rejected_avg
                FROM averages
            """)
            accepted_count, accepted_avg, rejected_count, rejected_avg, difference = cur.fetchone()
            print(f"Accepted: {accepted_count} reported GPAs, average {fmt(accepted_avg)}")
            print(f"Rejected: {rejected_count} reported GPAs, average {fmt(rejected_avg)}")
            print(f"Average GPA difference: {fmt(difference, spec='+.2f')}")


if __name__ == "__main__":
    main()
