"""Clean scraped Grad Café entries (from Module 2).

clean_data() takes the list of entries produced by scrape.py and:
  - trims stray whitespace in every text field,
  - decodes HTML entities (&amp; -> &) and removes leftover HTML tags,
  - makes every missing value the same thing: an empty string,
  - drops duplicate entries (same applicant URL),
  - never alters the raw "program" or "status" text, which are kept for traceability.

M4 CHANGE: the Module 2 file-reading/writing script part was removed; Pull Data only
uses clean_data(), and every line kept here must be covered by the tests.
"""

# ---- Block 1: imports and settings ----
import html
import re

RAW_FIELDS = ("program", "status")           # kept exactly as scraped
# Only known HTML tag names are removed, so text like "GPA < 3.5" is left alone.
TAG_PATTERN = re.compile(
    r"</?(?:p|br|b|i|u|a|em|strong|div|span|ul|ol|li|h[1-6]|img|table|tr|td|th)\b[^<>]*>",
    re.IGNORECASE,
)


# ---- Block 2: clean one text value ----
def _clean_text(value):
    """Return a tidy string: entities decoded, tags removed, whitespace trimmed.

    :param value: any scraped value.
    :returns: cleaned text (``""`` for ``None``).
    """
    if value is None:
        return ""
    text = html.unescape(str(value))
    text = TAG_PATTERN.sub("", text)
    return " ".join(text.split())             # collapses runs of spaces/newlines


# ---- Block 3: clean one entry (every field except the raw ones) ----
def _clean_entry(entry):
    """Clean every field of one entry, leaving the raw fields untouched.

    :param entry: one scraped entry dictionary.
    :returns: a new, cleaned dictionary.
    """
    cleaned = {}
    for key, value in entry.items():
        if key in RAW_FIELDS:
            cleaned[key] = "" if value is None else value
        else:
            cleaned[key] = _clean_text(value)
    return cleaned


# ---- Block 4: clean all entries and drop duplicates ----
def clean_data(entries):
    """Clean all entries and remove duplicates (same URL).

    :param entries: a list of scraped entry dictionaries.
    :returns: the cleaned list, first occurrence of each URL kept.
    """
    seen_urls = set()
    cleaned = []
    for entry in entries:
        item = _clean_entry(entry)
        if item.get("url") in seen_urls:      # M4 CHANGE: .get() so an entry without "url" can't crash
            continue                          # same applicant entry scraped twice
        seen_urls.add(item.get("url"))
        cleaned.append(item)
    return cleaned