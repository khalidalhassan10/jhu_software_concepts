"""scrape.py - Module 2: Grad Cafe scraper (part 1: parsing).

For now this parses a results page saved from Chrome (html.html) into a
list of dictionaries and saves them to JSON. The page-fetching loop,
scrape_data(), is added next.
"""
import json
import re

from bs4 import BeautifulSoup

BASE_URL = "https://www.thegradcafe.com"

# Patterns for the badge row. re.compile builds a pattern once so it can be reused.
TERM_PATTERN = re.compile(r"(Fall|Spring|Summer|Winter)\s+\d{4}")
# "Accepted on Sep 11" -> group 1 = "Accepted", group 2 = "Sep 11"
DECISION_PATTERN = re.compile(r"^(Accepted|Rejected|Wait listed|Interview|Other)(?:\s+on\s+(.*))?$")


def _empty_entry():
    """Return a dictionary with every field present and empty,
    so that all entries share exactly the same keys."""
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

    # Cell 0: university
    entry["university"] = cells[0].get_text(" ", strip=True)

    # Cell 1: program in the first <span>, degree in the second
    spans = cells[1].find_all("span")
    if spans:
        entry["program_name"] = spans[0].get_text(strip=True)
    if len(spans) > 1:
        entry["Degree"] = spans[1].get_text(strip=True)
    entry["program"] = f"{entry['program_name']}, {entry['university']}"

    # Cell 2: date the entry was added
    entry["date_added"] = cells[2].get_text(strip=True)

    # Cell 3: decision badge, split into decision and date
    entry["status"] = cells[3].get_text(" ", strip=True)
    match = DECISION_PATTERN.match(entry["status"])
    if match:
        entry["decision"] = match.group(1)
        entry["decision_date"] = match.group(2) or ""

    # Link to the applicant's own page
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
        # The decision badge repeats the main row, so it is ignored here.


def _parse_page(html):
    """Turn one page of HTML into a list of entry dictionaries."""
    soup = BeautifulSoup(html, "html.parser")
    entries = []
    current = None

    for row in soup.find_all("tr"):
        if _is_main_row(row):
            current = _parse_main_row(row)   # a new applicant starts
            entries.append(current)
        elif current is None:
            continue                         # header row, before any applicant
        elif row.find("p") is not None:
            current["comments"] = row.find("p").get_text(" ", strip=True)
        elif row.find("div", class_="tw-flex-wrap") is not None:
            _parse_badge_row(row, current)

    return entries


def save_data(entries, filename="applicant_data.json"):
    """Write the list of entries to a JSON file."""
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(entries, file, indent=2, ensure_ascii=False)


def load_data(filename="applicant_data.json"):
    """Read the list of entries back from a JSON file."""
    with open(filename, encoding="utf-8") as file:
        return json.load(file)


if __name__ == "__main__":
    with open("html.html", encoding="utf-8") as file:
        page_html = file.read()

    results = _parse_page(page_html)
    print(f"Parsed {len(results)} entries")
    print(json.dumps(results[:2], indent=2))
    save_data(results, "test_output.json")