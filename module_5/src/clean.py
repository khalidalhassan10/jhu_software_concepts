"""Clean scraped Grad Café entries (from Module 2).

clean_data() takes the list of entries produced by scrape.py and:
  - trims stray whitespace in every text field,
  - decodes HTML entities (&amp; -> &) and removes leftover HTML tags,
  - makes every missing value the same thing: an empty string,
  - drops duplicate entries (same applicant URL),
  - never alters the raw "program" or "status" text, which are kept for traceability.

Pull Data calls clean_data() on every page it reads.
"""


import html
import re

RAW_FIELDS = ("program", "status")

TAG_PATTERN = re.compile(
    r"</?(?:p|br|b|i|u|a|em|strong|div|span|ul|ol|li|h[1-6]|img|table|tr|td|th)\b[^<>]*>",
    re.IGNORECASE,
)


def _clean_text(value):
    """Return a tidy string: entities decoded, tags removed, whitespace trimmed.

    :param value: any scraped value.
    :returns: cleaned text (``""`` for ``None``).
    """
    if value is None:
        return ""
    text = html.unescape(str(value))
    text = TAG_PATTERN.sub("", text)
    return " ".join(text.split())


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


def clean_data(entries):
    """Clean all entries and remove duplicates (same URL).

    :param entries: a list of scraped entry dictionaries.
    :returns: the cleaned list, first occurrence of each URL kept.
    """
    seen_urls = set()
    cleaned = []
    for entry in entries:
        item = _clean_entry(entry)
        if item.get("url") in seen_urls:
            continue
        seen_urls.add(item.get("url"))
        cleaned.append(item)
    return cleaned
