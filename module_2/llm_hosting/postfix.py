"""postfix.py - second post-processing pass over the LLM output (no model calls).

Why: app.py's post-processor title-cases every name before checking the
canonical list (breaking acronyms: ETH -> Eth, CUNY -> Cuny), capitalizes small
words ("At", "And"), and its fuzzy matcher (cutoff 0.84) can map a name to a
near neighbour ("Geological Sciences" -> "Biological Sciences"). The model itself
sometimes truncates program names at a comma or changes their meaning.

Rules applied to every row, in order:
  University
    1. If the site's own university text already matches the canonical list
       (case-insensitive), use that canonical spelling.
    2. Otherwise: known fixes -> small words lowered -> acronyms restored from
       the site's text -> known fixes again -> close match on the canonical list.
  Program
    1. If the site's own program text already matches the canonical list, use it.
    2. If the model's answer shares less than half its characters with the
       site's text and the site's text is not an abbreviation, keep the site's
       text (title-cased, small words lowered). This catches truncations
       ("Black, Race, and Ethnic Studies" -> "Black") and meaning changes
       ("German" -> "Geometry").
    3. Otherwise keep the model's answer, small words lowered.

Run from module_2 (after run_llm.py --merge):  python llm_hosting/postfix.py
This pass is deterministic: running it again changes nothing.
"""
import difflib
import json
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


def _load_canon(path):
    """Return the canonical names as a list, plus a lowercase -> canonical lookup."""
    names = [line.strip() for line in open(path, encoding="utf-8") if line.strip()]
    return names, {name.lower(): name for name in names}


def _lower_small_words(name):
    """'Icahn School of Medicine At Mount Sinai' -> '... at Mount Sinai'."""
    return SMALL_WORDS.sub(lambda m: m.group(1).lower(), name)


def _restore_acronyms(name, original):
    """Put back all-caps tokens (ETH, UCSB, NYU) that appear in the site's own text."""
    acronyms = {t.strip("(),") for t in original.split()
                if t.strip("(),").isupper() and 2 <= len(t.strip("(),")) <= 6}
    words = []
    for word in name.split(" "):
        core = word.strip("(),")
        if core.upper() in acronyms:
            word = word.replace(core, core.upper())
        words.append(word)
    return " ".join(words)


def _close_match(name, canon):
    """Exact match on the canonical list, else a close match, else unchanged."""
    if name in canon:
        return name
    match = difflib.get_close_matches(name, canon, n=1, cutoff=0.9)
    return match[0] if match else name


def _similarity(a, b):
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()


def fix_university(model_value, site_value, canon, canon_lookup):
    """Rules 1-2 for the university field (see module docstring)."""
    if site_value.strip().lower() in canon_lookup:
        return canon_lookup[site_value.strip().lower()]
    value = FIXES.get(model_value, model_value)
    value = _lower_small_words(value)
    value = _restore_acronyms(value, site_value)
    value = FIXES.get(value, value)
    return _close_match(value, canon)


def fix_program(model_value, site_value, canon_lookup):
    """Rules 1-3 for the program field (see module docstring)."""
    site = site_value.strip()
    if site.lower() in canon_lookup:
        return canon_lookup[site.lower()]
    if site and len(site) > 4 and _similarity(site, model_value) < 0.5:
        return _lower_small_words(site.title())
    return _lower_small_words(model_value)


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

    json.dump(rows, open(DATA, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"Changed {changed} of {len(rows)} rows")