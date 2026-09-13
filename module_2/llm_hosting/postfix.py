"""postfix.py - second post-processing pass over the LLM output (no model calls).

app.py's post-processor title-cases every name before checking the canonical
list, which breaks acronyms (ETH -> Eth, CUNY -> Cuny, EPFL -> Epfl) and
capitalizes small words ("At", "And"). This pass repairs those cases:

  1. known fixes for variants seen in the output (see FIXES),
  2. small connecting words lowered (at, and, in, de, for, the),
  3. acronyms restored using the original scraped university text,
  4. exact / close match against the (extended) canonical list.

Run from module_2:  python llm_hosting/postfix.py
"""
import difflib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "llm_extend_applicant_data.json"
CANON_FILE = HERE / "canon_universities.txt"

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
    "CSU East Bay": "California State University, East Bay",
}
SMALL_WORDS = re.compile(r"(?<!^)\b(At|And|In|De|For|The|Du|Des|Der)\b")


def _lower_small_words(name):
    """'Icahn School of Medicine At Mount Sinai' -> '... at Mount Sinai'."""
    return SMALL_WORDS.sub(lambda m: m.group(1).lower(), name)


def _restore_acronyms(name, original):
    """Put back all-caps tokens (ETH, UCSB, NYU) that appear in the original text."""
    acronyms = {t.strip("(),") for t in original.split()
                if t.strip("(),").isupper() and 2 <= len(t.strip("(),")) <= 6}
    words = []
    for word in name.split(" "):
        core = word.strip("(),")
        if core.upper() in acronyms:
            word = word.replace(core, core.upper())
        words.append(word)
    return " ".join(words)


def _canonical(name, canon):
    """Exact match on the canonical list, else a close match, else unchanged."""
    if name in canon:
        return name
    match = difflib.get_close_matches(name, canon, n=1, cutoff=0.9)
    return match[0] if match else name


if __name__ == "__main__":
    canon = [line.strip() for line in open(CANON_FILE, encoding="utf-8") if line.strip()]
    rows = json.load(open(DATA, encoding="utf-8"))

    changed = 0
    for row in rows:
        uni = row["llm-generated-university"]
        prog = row["llm-generated-program"]

        new_uni = FIXES.get(uni, uni)
        new_uni = _lower_small_words(new_uni)
        new_uni = _restore_acronyms(new_uni, row.get("university", ""))
        new_uni = _canonical(new_uni, canon)
        new_prog = _lower_small_words(prog)

        if new_uni != uni or new_prog != prog:
            changed += 1
        row["llm-generated-university"] = new_uni
        row["llm-generated-program"] = new_prog

    json.dump(rows, open(DATA, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"Updated {changed} of {len(rows)} rows")