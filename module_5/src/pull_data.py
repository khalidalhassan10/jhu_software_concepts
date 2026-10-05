"""Pull Data: find Grad Café entries newer than the database and insert them.

It is split into small functions so tests can replace the parts that touch the
internet (the page fetcher) or the database, and so the Flask app can call them directly.
"""


import sys
import time

import psycopg
import urllib3
from psycopg import sql

from src import scrape
from src.clean import clean_data
from src.db_config import clamp_limit, get_database_url
from src.load_data import TABLE, insert_rows, result_id


MAX_PAGES = 40
STOP_AFTER_KNOWN_PAGES = 2
PULL_ERRORS = (RuntimeError, OSError, psycopg.Error, urllib3.exceptions.HTTPError)

EXISTING_IDS = sql.SQL("SELECT {key} FROM {table} WHERE {key} = ANY(%s) LIMIT %s").format(
    key=sql.Identifier("p_id"), table=TABLE
)


def existing_ids(candidate_ids, database_url=None):
    """Return which of ``candidate_ids`` are already stored (one small query per page).

    :param candidate_ids: the p_ids found on one results page (``None`` values are ignored).
    :param database_url: optional URL overriding DATABASE_URL.
    :returns: the set of those p_ids that the table already holds.
    """
    ids = sorted({p_id for p_id in candidate_ids if p_id is not None})
    if not ids:
        return set()
    with psycopg.connect(get_database_url(database_url)) as conn:
        rows = conn.execute(EXISTING_IDS, (ids, clamp_limit(len(ids))))
        return {row[0] for row in rows}


def scrape_new(find_existing, fetch_page, start_url=scrape.START_URL, max_pages=MAX_PAGES):
    """Collect cleaned entries that are not stored yet.

    Stops after ``STOP_AFTER_KNOWN_PAGES`` pages in a row with nothing new, when there
    is no next page, or after ``max_pages`` pages.

    :param find_existing: function ``list of p_ids -> set of those already stored``.
    :param fetch_page: function ``url -> html``.
    :param start_url: the first (newest) results page.
    :param max_pages: safety cap on pages read.
    :returns: the list of new, cleaned entries.
    :raises RuntimeError: on a verification page or a page with no entries.
    """
    new_entries = []
    seen = set()
    url = start_url
    pages_without_new = 0
    for page_number in range(1, max_pages + 1):
        html = fetch_page(url)
        if scrape.is_challenge_page(html):
            raise RuntimeError(
                "Grad Café showed a verification page. Verify it in Chrome, then try again."
            )
        entries = clean_data(scrape.parse_page(html))
        if not entries:
            raise RuntimeError(
                "Grad Café returned no application entries. Check the page before retrying."
            )

        ids = [result_id(entry.get("url")) for entry in entries]
        stored = find_existing([p_id for p_id in ids if p_id is not None])
        fresh = [
            entry for entry, p_id in zip(entries, ids)
            if p_id is not None and p_id not in stored and p_id not in seen
        ]
        new_entries.extend(fresh)
        seen.update(p_id for p_id in ids if p_id is not None)
        print(f"Page {page_number}: {len(fresh)} new entries", flush=True)

        pages_without_new = 0 if fresh else pages_without_new + 1
        if pages_without_new >= STOP_AFTER_KNOWN_PAGES:
            break
        next_url = scrape.find_next_url(html, url)
        if not next_url or next_url == url:
            break
        url = next_url
    return new_entries


def fetch(url, use_chrome):
    """Fetch one page with urllib3, or through the verified Chrome window.

    :raises RuntimeError: if the page could not be fetched.
    """
    if use_chrome:
        html = scrape.fetch_with_chrome(url)
        if not html:
            raise RuntimeError(
                "Chrome could not fetch the page. Open and verify Grad Café in Chrome first."
            )
        return html
    status, html = scrape.fetch_with_urllib3(url)
    if status != 200 or not html:
        raise RuntimeError(f"Grad Café returned HTTP {status}. No more pages were requested.")
    return html


def live_fetcher():
    """Check robots.txt, probe the site once, and return a ``url -> html`` function.

    The probe decides between urllib3 and Chrome (403 means Chrome). The returned
    function waits ``scrape.DELAY_SECONDS`` between pages to be polite to the site.

    :raises RuntimeError: if robots.txt does not allow scraping or the site errors.
    """
    if not scrape.check_robots():
        raise RuntimeError("robots.txt could not be confirmed to permit /survey/. Pull stopped.")
    status, first_html = scrape.fetch_with_urllib3(scrape.START_URL)
    if status == 403:
        use_chrome = True
    elif status == 200 and first_html:
        use_chrome = False
    else:
        raise RuntimeError(f"Grad Café returned HTTP {status}. Pull stopped.")

    saved = {scrape.START_URL: first_html} if first_html else {}

    def fetch_page(url):
        if url in saved:
            return saved.pop(url)
        time.sleep(scrape.DELAY_SECONDS)
        return fetch(url, use_chrome)

    return fetch_page


def main(database_url=None):
    """Pull new entries from Grad Café and insert them; print a summary.

    :param database_url: optional URL overriding DATABASE_URL.
    :returns: the number of rows inserted.
    """
    url = get_database_url(database_url)
    rows = scrape_new(lambda ids: existing_ids(ids, url), live_fetcher())
    inserted = insert_rows(rows, url)
    print(f"Pull complete: {inserted} new entries. Refresh the analysis to see updates.")
    return inserted


if __name__ == "__main__":
    try:
        main()
    except PULL_ERRORS as exc:
        print(f"Pull failed: {exc}", file=sys.stderr)
        sys.exit(1)
