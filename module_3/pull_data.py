"""Fetch recent Grad Café entries and add new ones to the existing database."""
import math
import re
import sys
import time
from datetime import datetime

import psycopg

import scrape
from clean import clean_data
from db_config import settings


MAX_PAGES = 40

INSERT_NEW = """
INSERT INTO applicants (
    p_id, program, comments, date_added, url, status, term,
    us_or_international, gpa, gre, gre_v, gre_aw, degree,
    llm_generated_program, llm_generated_university
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (p_id) DO NOTHING
"""


def optional_text(value):
    value = "" if value is None else str(value).strip()
    return value or None


def optional_number(value):
    try:
        number = float(str(value).replace(",", ""))
        return number if math.isfinite(number) else None
    except (ValueError, TypeError):
        return None


def optional_date(value):
    try:
        return datetime.strptime(str(value).strip(), "%b %d, %Y").date()
    except (ValueError, TypeError):
        return None


def result_id(entry):
    match = re.search(
        r"/result/(\d+)(?:/)?(?:\?.*)?$",
        entry.get("url", ""),
    )
    return int(match.group(1)) if match else None


def insert_new_entries(entries, connection):
    """Insert new entries without changing existing database rows."""
    inserted = 0

    with connection.cursor() as cur:
        for entry in entries:
            identifier = result_id(entry)
            if identifier is None:
                continue

            values = (
                identifier,
                optional_text(entry.get("program")),
                optional_text(entry.get("comments")),
                optional_date(entry.get("date_added")),
                optional_text(entry.get("url")),
                optional_text(entry.get("status")),
                optional_text(entry.get("term")),
                optional_text(entry.get("US/International")),
                optional_number(entry.get("GPA")),
                optional_number(entry.get("GRE")),
                optional_number(entry.get("GRE V")),
                optional_number(entry.get("GRE AW")),
                optional_text(entry.get("Degree")),
                None,
                None,
            )

            cur.execute(INSERT_NEW, values)
            inserted += cur.rowcount

    connection.commit()
    return inserted


def fetch(url, use_chrome):
    if use_chrome:
        html = scrape._fetch_with_chrome(url)
        if not html:
            raise RuntimeError(
                "Chrome could not fetch the page. "
                "Open and verify Grad Café in Chrome first."
            )
        return html

    status, html = scrape._fetch_with_urllib3(url)
    if status != 200 or not html:
        raise RuntimeError(
            f"Grad Café returned HTTP {status}. "
            "No more pages were requested."
        )

    return html


def pull():
    if not scrape._check_robots():
        raise RuntimeError(
            "robots.txt could not be confirmed to permit /survey/. "
            "Pull stopped."
        )

    # Start at the newest page. The old Module 2 progress file points
    # to older pages and would miss new submissions.
    url = scrape.START_URL
    status, html = scrape._fetch_with_urllib3(url)

    if status == 403:
        use_chrome = True
        html = fetch(url, use_chrome)
    elif status == 200 and html:
        use_chrome = False
    else:
        raise RuntimeError(
            f"Grad Café returned HTTP {status}. Pull stopped."
        )

    added = 0
    pages = 0
    known_pages = 0

    with psycopg.connect(**settings()) as connection:
        with connection.cursor() as cur:
            cur.execute("SELECT p_id FROM applicants")
            known = {row[0] for row in cur.fetchall()}

        while url and pages < MAX_PAGES:
            if scrape._is_challenge_page(html):
                raise RuntimeError(
                    "Grad Café showed a verification page. "
                    "Verify it in Chrome, then try again."
                )

            raw_entries = scrape._parse_page(html)
            if not raw_entries:
                raise RuntimeError(
                    "Grad Café returned no application entries. "
                    "Check the page before retrying."
                )

            entries = clean_data(raw_entries)

            fresh = [
                entry
                for entry in entries
                if result_id(entry) is not None
                and result_id(entry) not in known
            ]

            inserted = insert_new_entries(fresh, connection)
            added += inserted

            known.update(
                result_id(entry)
                for entry in entries
                if result_id(entry) is not None
            )

            pages += 1
            print(f"Page {pages}: {inserted} new entries", flush=True)

            known_pages = known_pages + 1 if not fresh else 0
            if known_pages >= 2:
                break

            next_url = scrape._find_next_url(html, url)
            if not next_url or next_url == url:
                break

            url = next_url
            time.sleep(scrape.DELAY_SECONDS)
            html = fetch(url, use_chrome)

    print(
        f"Pull complete: {added} new entries across {pages} pages. "
        "Refresh the analysis to see updates."
    )


if __name__ == "__main__":
    try:
        pull()
    except Exception as exc:
        print(f"Pull failed: {exc}", file=sys.stderr)
        sys.exit(1)