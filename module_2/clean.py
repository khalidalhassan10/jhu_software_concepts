"""clean.py - Module 2: clean the scraped Grad Cafe data.

clean_data() takes the list of entries produced by scrape.py and:
  - trims stray whitespace in every text field,
  - decodes any HTML entities (&amp; -> &) and removes any leftover tags,
  - makes every missing value the same thing: an empty string,
  - drops exact duplicate entries (same applicant URL),
  - never alters the raw "program" or "status" text, which are kept for traceability.

Run:  python clean.py        (reads applicant_data.json, writes it back cleaned)
"""
import html
import json
import re

DATA_FILE = "applicant_data.json"
RAW_FIELDS = ("program", "status")           # kept exactly as scraped
TAG_PATTERN = re.compile(r"<[^>]+>")          # any leftover <tag>


def load_data(filename=DATA_FILE):
    """Read the list of entries from a JSON file."""
    with open(filename, encoding="utf-8") as file:
        return json.load(file)


def _clean_text(value):
    """Return a tidy string: entities decoded, tags removed, whitespace trimmed."""
    if value is None:
        return ""
    text = html.unescape(str(value))
    text = TAG_PATTERN.sub("", text)
    return " ".join(text.split())             # collapses runs of spaces/newlines


def _clean_entry(entry):
    """Clean every field of one entry, leaving the raw fields untouched."""
    cleaned = {}
    for key, value in entry.items():
        if key in RAW_FIELDS:
            cleaned[key] = "" if value is None else value
        else:
            cleaned[key] = _clean_text(value)
    return cleaned


def clean_data(entries):
    """Clean all entries and remove duplicates. Returns the cleaned list."""
    seen_urls = set()
    cleaned = []
    for entry in entries:
        item = _clean_entry(entry)
        if item["url"] in seen_urls:
            continue                          # same applicant entry scraped twice
        seen_urls.add(item["url"])
        cleaned.append(item)
    return cleaned


def _report(before, after):
    """Print a short summary of what the cleaning did, for the README."""
    print(f"Entries before: {len(before)}, after: {len(after)}, duplicates removed: {len(before) - len(after)}")
    for field in ("comments", "GPA", "GRE", "GRE V", "GRE AW", "term", "US/International", "decision_date"):
        filled = sum(1 for e in after if e.get(field))
        print(f"  {field:<18} present in {filled:>6} entries")


if __name__ == "__main__":
    raw_entries = load_data()
    clean_entries = clean_data(raw_entries)
    _report(raw_entries, clean_entries)
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(clean_entries, file, indent=2, ensure_ascii=False)
    print(f"Saved cleaned data to {DATA_FILE}")