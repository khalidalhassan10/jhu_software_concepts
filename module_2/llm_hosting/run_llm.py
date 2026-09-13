"""run_llm.py - Run the instructor's app.py standardizer over applicant_data.json efficiently.

Why this exists: app.py processes rows one at a time at about 3 seconds each, and
30,000 rows would take longer than a day. Many rows share the exact same "program"
text, and app.py decodes deterministically (temperature 0), so the same text gets
the same answer. This script therefore:

  1. Loads ../applicant_data.json and collects the unique "program" strings
     (12,065 of the 30,000 rows).
  2. Skips any strings already answered in an earlier run (resume support).
  3. Splits the rest into WORKERS chunk files and runs one copy of app.py per
     chunk at the same time, each limited to THREADS_PER_WORKER CPU threads.
  4. Merges the answers back onto every row and writes
     ../llm_extend_applicant_data.json, the assignment's cleaned output.
     If any string has no cached answer (or an answer missing a field the site
     provided), the output is left untouched and the partial result goes to a
     separate file instead.

Cache policy: answers are keyed by the input string. If app.py, the model, or
the canonical lists change, delete work/ to reprocess every string.

Run:   python run_llm.py            start, or resume after a stop
       python run_llm.py --merge    only rebuild the output from finished results
Check: cat work/out_*.jsonl | wc -l   (strings finished so far)
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
INPUT = HERE.parent / "applicant_data.json"
OUTPUT = HERE.parent / "llm_extend_applicant_data.json"
WORK = HERE / "work"            # chunk inputs and outputs live here
WORKERS = 2
THREADS_PER_WORKER = 5          # 2 x 5 = the Mac's 10 cores


def _load_done():
    """Read every finished result from earlier runs: program text -> (program, university)."""
    done = {}
    for path in WORK.glob("out_*.jsonl"):
        with open(path, encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue        # a half-written line from an interrupted run
                done[row["program"]] = (
                    row.get("llm-generated-program", ""),
                    row.get("llm-generated-university", ""),
                )
    return done


def _run_workers(pending):
    """Split the pending strings into chunks and run app.py on each chunk in parallel."""
    WORK.mkdir(exist_ok=True)
    run_id = time.strftime("%Y%m%d_%H%M%S")
    chunks = [pending[i::WORKERS] for i in range(WORKERS)]   # deal them out like cards
    processes = []

    for index, chunk in enumerate(chunks):
        if not chunk:
            continue
        in_path = WORK / f"in_{run_id}_{index}.json"
        out_path = WORK / f"out_{run_id}_{index}.jsonl"
        with open(in_path, "w", encoding="utf-8") as file:
            json.dump([{"program": text} for text in chunk], file, ensure_ascii=False)

        env = dict(os.environ, N_THREADS=str(THREADS_PER_WORKER))
        command = [sys.executable, "app.py", "--file", str(in_path), "--out", str(out_path)]
        processes.append(subprocess.Popen(command, cwd=HERE, env=env))
        print(f"Worker {index}: {len(chunk)} strings -> {out_path.name}")

    failed = 0
    for process in processes:
        process.wait()
        if process.returncode != 0:
            failed += 1
            print(f"Warning: a worker exited with code {process.returncode}; rerun run_llm.py to finish its strings.")
    return failed


def _write_json_atomic(path, data):
    """Write to a temporary file, then rename, so an interruption never leaves a half-written file."""
    temp = path.with_suffix(path.suffix + ".tmp")
    with open(temp, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
    os.replace(temp, path)


def _merge(done):
    """Attach the standardized fields to every row and write the cleaned output file.
    Returns True when every row received an answer."""
    with open(INPUT, encoding="utf-8") as file:
        rows = json.load(file)

    missing = 0
    for row in rows:
        program, university = done.get(row["program"], ("", ""))
        # An answer is unusable if a field the site provided came back empty;
        # an empty field is fine only where the site itself had nothing
        # (e.g. the rows with no program name).
        program_bad = bool(row.get("program_name", "").strip()) and not program
        university_bad = bool(row.get("university", "").strip()) and not university
        if row["program"] not in done or program_bad or university_bad:
            missing += 1
        row["llm-generated-program"] = program
        row["llm-generated-university"] = university

    if missing and OUTPUT.exists():
        partial = OUTPUT.with_name("llm_extend_applicant_data.partial.json")
        _write_json_atomic(partial, rows)
        print(f"{missing} rows still without LLM output; kept the existing {OUTPUT.name} "
              f"and wrote the partial result to {partial.name}")
        return False
    _write_json_atomic(OUTPUT, rows)
    print(f"Wrote {len(rows)} rows to {OUTPUT.name}; {missing} rows still without LLM output")
    return missing == 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run app.py over the unique program strings in parallel.")
    parser.add_argument("--merge", action="store_true", help="Only merge finished results into the output file.")
    args = parser.parse_args()

    with open(INPUT, encoding="utf-8") as file:
        unique = sorted({row["program"] for row in json.load(file)})

    done = _load_done()
    pending = [text for text in unique if text not in done]
    print(f"{len(unique)} unique strings, {len(done)} already done, {len(pending)} to go")

    if pending and not args.merge:
        _run_workers(pending)
        done = _load_done()

    complete = _merge(done)
    sys.exit(0 if complete else 1)