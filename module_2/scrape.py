"""scrape.py - Module 2: Grad Cafe scraper.

How it works:
  1. Check robots.txt (urllib3 + urllib.robotparser) before anything else.
  2. Try to fetch the results page with urllib3. If the site refuses (403 from
     Cloudflare), switch to capturing pages from a Chrome window that you have
     already verified by hand. Chrome is driven with a small AppleScript.
  3. Parse each page into dictionaries (BeautifulSoup + regex + string methods).
  4. Find the "next page" link by inspecting each link's cursor with urllib.parse.
  5. Save every few pages and remember where we are, so a restart resumes.

Run:  python scrape.py
"""
import base64
import json
import re
import subprocess
import time
import urllib.robotparser
from urllib.parse import parse_qs, urljoin, urlparse

import urllib3
from bs4 import BeautifulSoup

# ---------------------------------------------------------------- settings ---
BASE_URL = "https://www.thegradcafe.com"
START_URL = BASE_URL + "/survey/"
ROBOTS_URL = BASE_URL + "/robots.txt"
USER_AGENT = "jhu-605.256-module2-student-scraper"
TARGET_ENTRIES = 30000
DELAY_SECONDS = 2          # politeness pause between pages
SAVE_EVERY = 10            # pages between saves to disk
DATA_FILE = "applicant_data.json"
PROGRESS_FILE = "progress.json"

# One PoolManager for every urllib3 request (urllib3 user guide recommends this).
http = urllib3.PoolManager(
    headers={"User-Agent": USER_AGENT},
    retries=urllib3.Retry(total=1),   # do not hammer the site if it says no
    timeout=15.0,
)

# Patterns for the badge row.
TERM_PATTERN = re.compile(r"(Fall|Spring|Summer|Winter)\s+\d{4}")
# "Accepted on Sep 11" -> group 1 = "Accepted", group 2 = "Sep 11"
DECISION_PATTERN = re.compile(r"^(Accepted|Rejected|Wait listed|Interview|Other)(?:\s+on\s+(.*))?$")

# AppleScript that asks Chrome to open a URL in a new tab, wait for it to load,
# return the page's HTML, and close the tab. __URL__ is replaced at run time.
CHROME_SCRIPT = '''
tell application "Google Chrome"
    set theTab to make new tab at end of tabs of front window with properties {URL:"__URL__"}
    set waited to 0
    repeat while (loading of theTab) and waited < 30
        delay 0.5
        set waited to waited + 0.5
    end repeat
    delay 1
    set pageHTML to execute theTab javascript "document.documentElement.outerHTML"
    close theTab
    return pageHTML
end tell
'''


# ------------------------------------------------------------ robots.txt ---
def _check_robots():
    """Fetch robots.txt with urllib3 and confirm this scraper may read /survey/."""
    response = http.request("GET", ROBOTS_URL)
    print(f"robots.txt status: {response.status}")
    if response.status != 200:
        print("robots.txt could not be fetched programmatically; "
              "relying on the manual check (screenshot.jpg, see README).")
        return True
    parser = urllib.robotparser.RobotFileParser()
    parser.parse(response.data.decode("utf-8").splitlines())
    allowed = parser.can_fetch(USER_AGENT, START_URL)
    print(f"robots.txt allows {START_URL}: {allowed}")
    return allowed


# -------------------------------------------------------------- fetching ---
def _fetch_with_urllib3(url):
    """Try to fetch a page directly. Returns HTML text, or None if the site refuses."""
    response = http.request("GET", url)
    if response.status == 200:
        return response.data.decode("utf-8")
    print(f"urllib3 received status {response.status} for {url}")
    return None


def _fetch_with_chrome(url):
    """Ask the open, already-verified Chrome window for the page's HTML."""
    script = CHROME_SCRIPT.replace("__URL__", url)
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if result.returncode != 0:
        print("Chrome capture failed:", result.stderr.strip())
        return None
    return result.stdout


# --------------------------------------------------------------- parsing ---
def _empty_entry():
    """A dictionary with every field present and empty, so all entries share the same keys."""
    return {
        "program": "",           # "Program, University" combined, for the LLM step
        "program_name": "",
        "university": "",
        "Degree": "",
        "comments": "",
        "date_added": "",
        "url": "",
        "status": "",            # raw decision text, e.g. "Accepted on Sep 11"
        "decision": "",          # "Accepted", "Rejected", "Wait listed", ...
        "decision_date": "",     # "Sep 11"
        "term": "",
        "US/International": "",
        "GPA": "",
        "GRE": "",
        "GRE V": "",
        "GRE AW": "",
    }


def _is_main_row(row):
    """The main row of an applicant is the one holding the /result/... link."""
    return row.find("a", href=re.compile(r"^/result/")) is not None


def _parse_main_row(row):
    """Read university, program, degree, date added, decision and URL from a main row."""
    entry = _empty_entry()
    cells = row.find_all("td")

    entry["university"] = cells[0].get_text(" ", strip=True)

    spans = cells[1].find_all("span")
    if spans:
        entry["program_name"] = spans[0].get_text(strip=True)
    if len(spans) > 1:
        entry["Degree"] = spans[1].get_text(strip=True)
    entry["program"] = f"{entry['program_name']}, {entry['university']}"

    entry["date_added"] = cells[2].get_text(strip=True)

    entry["status"] = cells[3].get_text(" ", strip=True)
    match = DECISION_PATTERN.match(entry["status"])
    if match:
        entry["decision"] = match.group(1)
        entry["decision_date"] = match.group(2) or ""

    link = row.find("a", href=re.compile(r"^/result/"))
    entry["url"] = BASE_URL + link["href"]
    return entry


def _parse_badge_row(row, entry):
    """Read term, applicant type, GPA and GRE scores from the badge row into the entry."""
    for badge in row.find_all("div", class_="tw-inline-flex"):
        text = badge.get_text(" ", strip=True)
        if TERM_PATTERN.match(text):
            entry["term"] = text
        elif text in ("American", "International", "Other"):
            entry["US/International"] = text
        elif text.startswith("GRE AW"):
            entry["GRE AW"] = text.replace("GRE AW", "").strip()
        elif text.startswith("GRE V"):
            entry["GRE V"] = text.replace("GRE V", "").strip()
        elif text.startswith("GRE"):
            entry["GRE"] = text.replace("GRE", "").strip()
        elif text.startswith("GPA"):
            entry["GPA"] = text.replace("GPA", "").strip()


def _parse_page(html):
    """Turn one page of HTML into a list of entry dictionaries."""
    soup = BeautifulSoup(html, "html.parser")
    entries = []
    current = None

    for row in soup.find_all("tr"):
        if _is_main_row(row):
            current = _parse_main_row(row)
            entries.append(current)
        elif current is None:
            continue
        elif row.find("p") is not None:
            current["comments"] = row.find("p").get_text(" ", strip=True)
        elif row.find("div", class_="tw-flex-wrap") is not None:
            _parse_badge_row(row, current)

    return entries


# ------------------------------------------------------------ next page ---
def _decode_cursor(cursor):
    """The cursor is base64 text holding JSON; decode it into a dictionary."""
    padded = cursor + "=" * (-len(cursor) % 4)
    return json.loads(base64.urlsafe_b64decode(padded))


def _find_next_url(html, current_url):
    """Return the URL of the next page by inspecting each cursor link's query string."""
    soup = BeautifulSoup(html, "html.parser")
    for link in soup.find_all("a", href=re.compile("cursor=")):
        full_url = urljoin(current_url, link["href"])
        query = parse_qs(urlparse(full_url).query)
        cursor = query.get("cursor", [""])[0]
        try:
            if _decode_cursor(cursor).get("_pointsToNextItems"):
                return full_url
        except (ValueError, json.JSONDecodeError):
            continue
    return None


# -------------------------------------------------------- save / resume ---
def save_data(entries, filename=DATA_FILE):
    """Write the list of entries to a JSON file."""
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(entries, file, indent=2, ensure_ascii=False)


def load_data(filename=DATA_FILE):
    """Read the list of entries back from a JSON file."""
    with open(filename, encoding="utf-8") as file:
        return json.load(file)


def _load_progress():
    """Where to continue from. First run starts at page one."""
    try:
        with open(PROGRESS_FILE, encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return {"next_url": START_URL, "pages_done": 0}


def _save_progress(next_url, pages_done):
    """Remember the next page to fetch so a restart resumes instead of starting over."""
    with open(PROGRESS_FILE, "w", encoding="utf-8") as file:
        json.dump({"next_url": next_url, "pages_done": pages_done}, file, indent=2)


# ------------------------------------------------------------- main loop ---
def scrape_data(target=TARGET_ENTRIES):
    """Collect applicant entries page by page until the target count is reached."""
    if not _check_robots():
        print("robots.txt disallows scraping /survey/ -- stopping.")
        return []

    try:
        entries = load_data()
    except FileNotFoundError:
        entries = []
    progress = _load_progress()
    url = progress["next_url"]
    pages_done = progress["pages_done"]
    print(f"Starting with {len(entries)} entries, {pages_done} pages done.")

    # Decide once how pages will be fetched: directly if the site allows it,
    # otherwise from the verified Chrome window (one polite probe request only).
    html = _fetch_with_urllib3(url)
    use_chrome = html is None
    if use_chrome:
        print("Direct requests are blocked. Capturing pages from Chrome instead.")

    empty_pages = 0
    while len(entries) < target and url:
        if html is None:
            html = _fetch_with_chrome(url) if use_chrome else _fetch_with_urllib3(url)
        if html is None:
            print("Could not fetch the page -- stopping.")
            break

        page_entries = _parse_page(html)
        if not page_entries:
            empty_pages += 1
            print("No entries on this page (verification page or end of results). Waiting...")
            html = None
            if empty_pages >= 3:
                print("Three empty pages in a row -- stopping.")
                break
            time.sleep(15)
            continue
        empty_pages = 0

        entries.extend(page_entries)
        pages_done += 1
        next_url = _find_next_url(html, url)
        print(f"Page {pages_done}: {len(page_entries)} entries (total {len(entries)})")

        if pages_done % SAVE_EVERY == 0:
            save_data(entries)
            _save_progress(next_url, pages_done)

        url = next_url
        html = None
        time.sleep(DELAY_SECONDS)

    save_data(entries)
    _save_progress(url, pages_done)
    return entries


if __name__ == "__main__":
    data = scrape_data()
    print(f"Done. {len(data)} entries saved to {DATA_FILE}")