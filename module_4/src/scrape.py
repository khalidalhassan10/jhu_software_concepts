"""Grad Café page fetching and parsing (from Module 2), used by Pull Data.

How it works:
  1. Check robots.txt (urllib3 + urllib.robotparser) before anything else.
  2. Fetch a results page with urllib3. If the site refuses (403 from Cloudflare),
     capture the page from a Chrome window you already verified by hand (AppleScript).
  3. Parse each page into dictionaries (BeautifulSoup + regex + string methods).
  4. Find the "next page" link by decoding each link's cursor.

Pull Data (pull_data.py) walks the pages; this module fetches and reads them.
"""
import base64
import json
import re
import subprocess
import urllib.robotparser
from urllib.parse import parse_qs, urljoin, urlparse

import urllib3
from bs4 import BeautifulSoup


BASE_URL = "https://www.thegradcafe.com"
START_URL = BASE_URL + "/survey/"
ROBOTS_URL = BASE_URL + "/robots.txt"
USER_AGENT = "jhu-605.256-module2-student-scraper"
DELAY_SECONDS = 2


http = urllib3.PoolManager(
    headers={"User-Agent": USER_AGENT},
    retries=urllib3.Retry(total=1),
    timeout=15.0,
)


TERM_PATTERN = re.compile(r"(Fall|Spring|Summer|Winter)\s+\d{4}")

DECISION_PATTERN = re.compile(r"^(Accepted|Rejected|Wait listed|Interview|Other)(?:\s+on\s+(.*))?$")


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


def _is_challenge_page(html):
    """True if the HTML is Cloudflare's verification page rather than site content."""
    lowered = html.lower()
    return "just a moment" in lowered or "verifying you are human" in lowered or "cf-chl" in lowered


ROBOTS_DIRECTIVE = re.compile(r"^\s*(user-agent|allow|disallow)\s*:", re.IGNORECASE | re.MULTILINE)


def _looks_like_robots(text):
    """A real robots.txt has directive lines such as 'User-agent:' and 'Disallow:'
    at the start of lines; prose that merely mentions a user agent does not."""
    directives = ROBOTS_DIRECTIVE.findall(text)
    kinds = {d.lower() for d in directives}
    return "user-agent" in kinds and ("allow" in kinds or "disallow" in kinds)


def _check_robots():
    """Read robots.txt (directly, or via Chrome only if the site answers 403 to scripts)
    and confirm this scraper may read /survey/. Stops unless a real robots.txt was
    read and it allows the path."""
    response = http.request("GET", ROBOTS_URL)
    print(f"robots.txt status: {response.status}")
    if response.status == 200:
        text = response.data.decode("utf-8")
    elif response.status == 403:
        print("robots.txt refused to a script (403); reading it through the verified Chrome window.")
        html = _fetch_with_chrome(ROBOTS_URL)
        if html is None:
            print("robots.txt could not be read through Chrome -- stopping.")
            return False
        text = BeautifulSoup(html, "html.parser").get_text()
    else:
        print(f"robots.txt answered {response.status} (rate limit or error) -- stopping.")
        return False
    if _is_challenge_page(text) or not _looks_like_robots(text):
        print("What was read is a verification page or not a robots.txt file -- stopping.")
        return False
    parser = urllib.robotparser.RobotFileParser()
    parser.parse(text.splitlines())
    allowed = parser.can_fetch(USER_AGENT, START_URL)
    print(f"robots.txt allows {START_URL}: {allowed}")
    return allowed


def _fetch_with_urllib3(url):
    """Fetch a page directly. Returns (status, html); html is None unless status is 200."""
    response = http.request("GET", url)
    if response.status == 200:
        return 200, response.data.decode("utf-8")
    print(f"urllib3 received status {response.status} for {url}")
    return response.status, None


def _fetch_with_chrome(url):
    """Ask the open, already-verified Chrome window for the page's HTML."""
    script = CHROME_SCRIPT.replace("__URL__", url)
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if result.returncode != 0:
        print("Chrome capture failed:", result.stderr.strip())
        return None
    return result.stdout


def _empty_entry():
    """A dictionary with every field present and empty, so all entries share the same keys."""
    return {
        "program": "",
        "program_name": "",
        "university": "",
        "Degree": "",
        "comments": "",
        "date_added": "",
        "url": "",
        "status": "",
        "decision": "",
        "decision_date": "",
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
