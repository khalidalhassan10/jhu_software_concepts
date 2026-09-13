"""postfix.py - second post-processing pass over the LLM output (no model calls).

Why: app.py's post-processor title-cases every name before checking the
canonical list (breaking acronyms: ETH -> Eth, CUNY -> Cuny), capitalizes small
words ("At", "And"), and its fuzzy matcher (cutoff 0.84) can map a name to a
near neighbour ("Geological Sciences" -> "Biological Sciences"). The model itself
often introduces typos ("Religion" -> "Religiion"), truncates program names at a
comma, or changes their meaning.

The site's own program and university fields (scraped from separate cells) are
the most reliable source, so the rules lean on them:

  Program
    1. Empty on the site -> empty here (missing data is not invented).
    2. Site text already on the canonical list -> that canonical spelling.
    3. Site text is an abbreviation (4 characters or fewer, e.g. "ECE") -> a
       known expansion if there is one, else a canonical model answer, else
       the site's text as written (an all-lowercase word is title-cased:
       "law" -> "Law"; acronyms keep their capitals: "EECS"). A model answer
       that is neither canonical nor an exact match is never trusted for an
       abbreviation, because the model cannot know what "BSS" or "DMA" stands
       for and tends to invent ("Bsst", "Dmar").
    4. Model's answer is on the canonical list -> kept (a real standardization).
    5. Otherwise the model changed a full name without landing on a canonical
       one (typo, truncation, hallucination) -> the site's text is kept,
       title-cased with small words lowered and acronyms preserved.
  University
    1. Site text already on the canonical list -> that canonical spelling.
    2. Otherwise: known fixes -> small words lowered -> acronyms restored from
       the site's text -> known fixes again -> close match on the canonical list.
    3. If the model's answer is the site's text plus extra comma-separated
       words ("Philadelphia, Yale" for "yale"), only the site's part is kept.
    4. If the result is the site's text with leading words dropped
       ("Medical University of South Carolina" -> "University of South
       Carolina"), the site's text is kept.

Run from module_2 (after run_llm.py --merge):  python llm_hosting/postfix.py
This pass is deterministic: running it again changes nothing.
"""
import difflib
import json
import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "llm_extend_applicant_data.json"
CANON_UNI_FILE = HERE / "canon_universities.txt"
CANON_PROG_FILE = HERE / "canon_programs.txt"

FIXES = {
    "Eth Zurich": "ETH Zurich",
    "Cuny": "City University of New York (CUNY)",
    "Cuny Graduate Center": "CUNY Graduate Center",
    "Nyu Steinhardt": "NYU Steinhardt",
    "Ecole Polytechnique Federale De Lausanne (Epfl)": "École Polytechnique Fédérale de Lausanne (EPFL)",
    "Ecole Polytechnique Federale De Lauhanne (Epfl)": "École Polytechnique Fédérale de Lausanne (EPFL)",
    "Suny Buffalo": "University at Buffalo (SUNY)",
    "Suny Stony Brook": "Stony Brook University (SUNY)",
    "Suny Albany": "University at Albany (SUNY)",
    "Washu/Wustl": "Washington University in St. Louis",
    "Ut Southwestern": "UT Southwestern Medical Center",
    "Mit Media Lab": "MIT Media Lab",
    "Ku Leuven": "KU Leuven",
    "University of California (Ucsb)": "University of California, Santa Barbara",
    "Stanford": "Stanford University",
    "Yale": "Yale University",
    "Princeton": "Princeton University",
    "Csu East Bay": "California State University, East Bay",
    "CSU East Bay": "California State University, East Bay",
}
SMALL_WORDS = re.compile(r"(?<!^)\b(At|And|In|De|For|The|Du|Des|Der|Of)\b")
ABBREVIATION_LENGTH = 4
ABBREVIATIONS = {                 # unambiguous short program names seen on the site
    "ECE": "Electrical and Computer Engineering",
    "EECS": "Electrical Engineering and Computer Science",
    "CS": "Computer Science",
    "EE": "Electrical Engineering",
    "ME": "Mechanical Engineering",
    "HCI": "Human-Computer Interaction",
    "MATH": "Mathematics",
    "BIO": "Biology",
    "LING": "Linguistics",
    "ARCH": "Architecture",
    "ECON": "Economics",
    "STAT": "Statistics",
    "PHYS": "Physics",
    "CHEM": "Chemistry",
}


def _load_canon(path):
    """Return the canonical names as a list, plus a lowercase -> canonical lookup."""
    names = [line.strip() for line in open(path, encoding="utf-8") if line.strip()]
    return names, {name.lower(): name for name in names}


def _lower_small_words(name):
    """'Icahn School of Medicine At Mount Sinai' -> '... at Mount Sinai'."""
    return SMALL_WORDS.sub(lambda m: m.group(1).lower(), name)


def _restore_acronyms(name, original):
    """Put back all-caps tokens (ETH, UCSB, BBS) that appear in the site's own text."""
    acronyms = {t.strip("(),") for t in original.split()
                if t.strip("(),").isupper() and 2 <= len(t.strip("(),")) <= 6}
    words = []
    for word in name.split(" "):
        core = word.strip("(),")
        if core.upper() in acronyms:
            word = word.replace(core, core.upper())
        words.append(word)
    return " ".join(words)


def _tidy_site_text(text):
    """Title-case the site's own text, keep small words lower and acronyms intact."""
    return _restore_acronyms(_lower_small_words(text.title()), text)


def _close_match(name, canon):
    """Exact match on the canonical list, else a close match, else unchanged."""
    if name in canon:
        return name
    match = difflib.get_close_matches(name, canon, n=1, cutoff=0.9)
    return match[0] if match else name


def fix_program(model_value, site_value, canon_lookup):
    """Program rules 1-5 (see module docstring)."""
    site = site_value.strip()
    if not site:
        return ""
    if site.lower() in canon_lookup:
        return canon_lookup[site.lower()]
    if len(site) <= ABBREVIATION_LENGTH:
        if site.upper() in ABBREVIATIONS:
            return ABBREVIATIONS[site.upper()]
        if model_value.lower() in canon_lookup:
            return canon_lookup[model_value.lower()]
        return site.title() if site.islower() else site
    if model_value.lower() in canon_lookup:
        return canon_lookup[model_value.lower()]
    if model_value.strip().lower() == site.lower():
        return _lower_small_words(model_value)
    return _tidy_site_text(site)


def fix_university(model_value, site_value, canon, canon_lookup):
    """University rules 1-4 (see module docstring)."""
    site = site_value.strip()
    if site.lower() in canon_lookup:
        return canon_lookup[site.lower()]
    value = model_value
    if site and "," in value:                 # "Philadelphia, Yale" for site text "yale"
        for part in value.split(","):
            if part.strip().lower() == site.lower():
                value = part.strip().title() if site.islower() else part.strip()
                break
    value = FIXES.get(value, value)
    value = _lower_small_words(value)
    value = _restore_acronyms(value, site)
    value = FIXES.get(value, value)
    value = _close_match(value, canon)
    if site and value.lower() != site.lower() and site.lower().endswith(value.lower()):
        return site                       # the model dropped leading words of the real name
    return value


def _write_json_atomic(path, data):
    """Write to a temporary file, then rename, so an interruption never leaves a half-written file."""
    temp = path.with_suffix(path.suffix + ".tmp")
    with open(temp, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
    os.replace(temp, path)


if __name__ == "__main__":
    canon_unis, uni_lookup = _load_canon(CANON_UNI_FILE)
    _, prog_lookup = _load_canon(CANON_PROG_FILE)
    rows = json.load(open(DATA, encoding="utf-8"))

    changed = 0
    for row in rows:
        new_uni = fix_university(row["llm-generated-university"], row.get("university", ""),
                                 canon_unis, uni_lookup)
        new_prog = fix_program(row["llm-generated-program"], row.get("program_name", ""), prog_lookup)
        if new_uni != row["llm-generated-university"] or new_prog != row["llm-generated-program"]:
            changed += 1
        row["llm-generated-university"] = new_uni
        row["llm-generated-program"] = new_prog

    _write_json_atomic(DATA, rows)
    print(f"Changed {changed} of {len(rows)} rows")