import json
import psycopg
from getpass import getpass
from datetime import datetime

def to_text(value):
    if value is None:  
        return None 

    return str(value).strip() or None 

def to_float(value):  
    value = to_text(value)  

    if value is None:  
        return None  

    try:  
        return float(value)  
    except ValueError:  
        return None


def to_date(value): 
    value = to_text(value)  

    if value is None:  
        return None  

    return datetime.strptime(value, "%b %d, %Y").date()

DATA_FILE = "llm_extend_applicant_data.json"

with open(DATA_FILE, encoding="utf-8") as file:
    applicants = json.load(file)

print(f"Read {len(applicants)} records from the JSON file.")








connection = psycopg.connect(
    dbname="gradcafe",
    user="postgres",
    host="localhost",
    port=5432,
    password=getpass("PostgreSQL password: "),
)


try:
    with connection.cursor() as cur:

        cur.execute("""
            CREATE TABLE IF NOT EXISTS applicants(
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
            );
        """)

        inserted = 0

        for applicant in applicants:
            p_id = int(applicant["url"].rstrip("/").split("/")[-1])

            values = (
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

            cur.execute(
                "INSERT INTO applicants ("
                "p_id, program, comments, date_added, url, "
                "status, term, us_or_international, gpa, gre, "
                "gre_v, gre_aw, degree, llm_generated_program, llm_generated_university"
                ") VALUES ("
                "%s, %s, %s, %s, %s, "
                "%s, %s, %s, %s, %s, "
                "%s, %s, %s, %s, %s"
                ") ON CONFLICT (p_id) DO NOTHING;",
                values,
            )

            inserted += cur.rowcount

        cur.execute("SELECT COUNT(*) FROM applicants;")  
        total = cur.fetchone()[0] 

    connection.commit()
finally:
    connection.close()

print(f"Inserted {inserted} new applicants.")  

print(f"Applicants stored in PostgreSQL: {total}")