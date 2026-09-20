import psycopg
from getpass import getpass

connection = psycopg.connect(
    dbname="gradcafe",
    user="postgres",
    host="localhost",
    port=5432,
    password=getpass("PostgreSQL password: "),
)

with connection.cursor() as cur:
    #Q1
    cur.execute("""
        SELECT COUNT(term) FROM applicants
        WHERE term ILIKE 'Fall 2026'

    """)
    print(f"Fall 2026 applicant count: {cur.fetchone()[0]}")

    #Q2
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

    print(f"Percent international: {cur.fetchone()[0]:.2f}%")


    #Q3
    #GPA
    cur.execute("""
        SELECT avg(gpa) from applicants

    """)
    print(f"Average GPA: {cur.fetchone()[0]:.2f}")

    #GRE Quantitative
    cur.execute("""
        SELECT avg(gre) from applicants
    """)
    print(f"Average GRE Quantitative: {cur.fetchone()[0]:.2f}")

    #GRE Verbal
    cur.execute("""
        SELECT avg(gre_v) from applicants
    """)
    print(f"Average GRE Verbal: {cur.fetchone()[0]:.2f}")
    
    #GRE Analytical Writing
    cur.execute("""
        SELECT avg(gre_aw) from applicants
    """)
    print(f"Average GRE Analytical Writing: {cur.fetchone()[0]:.2f}")

    #Q4
    cur.execute("""
    SELECT avg(gpa) FROM applicants
    WHERE us_or_international ILIKE 'American'
    AND term ILIKE 'Fall 2026'
    """)
    print(f"Average GPA of Americans for Fall 2026: {cur.fetchone()[0]:.2f}")

    #Q5
    cur.execute("""
        SELECT
            100.0 * COUNT(*) FILTER (
                WHERE status ILIKE 'Accepted%'
            )
            / NULLIF(COUNT(*), 0)
        FROM applicants
        WHERE term ILIKE 'Fall 2025'
    """)
    print(f"Fall 2025 acceptance percentage: {cur.fetchone()[0]:.2f}%")

    #Q6
    cur.execute("""
        SELECT avg(gpa) FROM applicants
        WHERE term ILIKE 'FALL 2026'
        AND status ILIKE 'Accepted%' 
    """)
    print(f"Average GPA of accepted applicants in Fall 2026: {cur.fetchone()[0]:.2f}")

    #Q7
    cur.execute("""
    SELECT COUNT(*)
    FROM applicants
    WHERE (program ILIKE '%Johns Hopkins%' 
    OR program ILIKE '%JHU%' )
    AND program ILIKE '%Computer Science%'
    AND degree ILIKE 'Masters'
    """)
    print(f"Applicants applied to Johns Hopkins University for a master's degree in Computer Science: {cur.fetchone()[0]}")

    #Q8
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
    print(f"Accepted PhD in Computer Science applicants in Fall 2026 in Georgetown, MIT, Stanford and CMU is: {q8_count}")


    #Q9
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

    q9_count=cur.fetchone()[0]
    print(f"Original-field count: {q8_count}")
    print(f"LLM-field count: {q9_count}")

    cur.execute(
    "SELECT %s::integer - %s::integer",
    (q9_count, q8_count),
    )
    difference = cur.fetchone()[0]
    print(f"Difference: {difference:+d}")


    #Part 3
    #Q10
    # For Fall 2026 Computer Science applicants, whats the percentage of masters
    # applicants and PHD applicants 

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

    masters_count, phd_count, total_count, masters_percentage, phd_percentage = cur.fetchone()
    print(f"Computer Science entries in Fall 2026: {total_count}")
    print(f"Masters: {masters_count} ({masters_percentage:.2f}%)")
    print(f"PhD: {phd_count} ({phd_percentage:.2f}%)")



    # Q11
    # Among Computer Science master’s entries, how does the average reported GPA 
    # compare between accepted and rejected entries?

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
    SELECT
    accepted_count,
    accepted_avg,
    rejected_count,
    rejected_avg,
    accepted_avg - rejected_avg
    FROM averages
""")

    accepted_count, accepted_avg, rejected_count, rejected_avg, difference = cur.fetchone()
    print(f"Accepted: {accepted_count} reported GPAs, average {accepted_avg:.2f}")
    print(f"Rejected: {rejected_count} reported GPAs, average {rejected_avg:.2f}")
    print(f"Average GPA difference: {difference:+.2f}")
