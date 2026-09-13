Module 2 - Assignment: Web Scraping (Grad Cafe)
605.256 Modern Software Concepts in Python
Name: Khaled Al-Hassan    JHED: kalhass2
Due: Sunday, September 13, 2026, 23:59 Eastern (as shown on Canvas)

------------------------------------------------------------
1. Overview
------------------------------------------------------------
This project scrapes 30,000 graduate-admissions results from
https://www.thegradcafe.com/survey/, parses each entry into a
dictionary with 16 fields, cleans the data, and standardizes the
program and university names with the instructor's local-LLM tool.

Deliverables in this folder:
  scrape.py                       scraping logic (scrape_data, save_data + helpers)
  clean.py                        cleaning logic (clean_data, load_data + helpers)
  applicant_data.json             30,000 scraped entries (cleaned)
  llm_extend_applicant_data.json  the same 30,000 entries + llm-generated-program
                                  and llm-generated-university
  llm_hosting/                    the instructor's LLM standardizer, plus run_llm.py,
                                  postfix.py, and work/ (per-string model outputs)
  screenshot.jpg                  robots.txt as displayed in the browser
  requirements.txt                exact package versions used
  html.html                       one results page saved from Chrome, used to
                                  develop the parser offline
  progress.json                   scraper checkpoint (last page reached)

------------------------------------------------------------
2. How to run
------------------------------------------------------------
Python 3.12 (3.10+ required). From module_2:

  pip install -r requirements.txt

Scraping (see section 4 for why Chrome is involved):
  1. Open https://www.thegradcafe.com/survey/ in Google Chrome and complete
     Cloudflare's "verify you are human" check once. Leave Chrome open.
  2. In Chrome: View > Developer > Allow JavaScript from Apple Events.
  3. python scrape.py
     Writes applicant_data.json and progress.json every 10 pages; if it is
     interrupted, running it again resumes from progress.json.

Cleaning:
  python clean.py            (rewrites applicant_data.json cleaned)

LLM standardization:
  Note: app.py downloads the TinyLlama model (~670 MB) into
  llm_hosting/models/ on first run; the model is not included in the repo.
  cd llm_hosting
  python run_llm.py          (runs app.py in parallel over the unique program
                              strings; writes ../llm_extend_applicant_data.json;
                              resumable)
  cd ..
  python llm_hosting/postfix.py   (second post-processing pass, see section 6)

------------------------------------------------------------
3. robots.txt compliance
------------------------------------------------------------
Before scraping I opened https://www.thegradcafe.com/robots.txt in the
browser (screenshot.jpg). The file has three parts:
  - A Cloudflare-managed block: "User-agent: *" is allowed everything
    ("Allow: /") with a Content-Signal line (search=yes, ai-train=no),
    and a list of named AI crawlers (GPTBot, ClaudeBot, CCBot, Bytespider,
    Amazonbot, Applebot-Extended, Google-Extended, meta-externalagent,
    CloudflareBrowserRenderingCrawler) that are disallowed everywhere.
  - A general block for all other agents disallowing only account pages:
    /signin, /register, /forgot-password, /reset-password,
    /confirm-password, /verify-email, /profile.
  - Full disallows for ia_archiver, dotbot and YandexBot.
The scraper's user agent ("jhu-605.256-module2-student-scraper") is none
of the named crawlers, so the "User-agent: *" rules apply, and the
/survey/ results pages are not disallowed. No account page was ever
requested. The scraper also checks this programmatically: _check_robots()
in scrape.py fetches robots.txt with urllib3 (or reads it through the
verified Chrome window if the site refuses scripts), parses it with
urllib.robotparser, and stops unless /survey/ is allowed for its user agent.
A 403 on the results page triggers the browser capture; any other refusal
(429 rate limit, server error) stops the run.
The data was collected for a course data-analysis exercise, not for
training an AI model.

Politeness: one page every DELAY_SECONDS (2 s) plus page-load time, a
single direct probe request (never repeated after the 403), retries
limited to 1, and the scraper stops on any failed fetch, on any non-403
refusal, or after three consecutive empty pages. No CAPTCHA, login, or rate
limit was bypassed by automation; Cloudflare's verification was completed
once by hand in Chrome.

------------------------------------------------------------
4. Approach: scraping
------------------------------------------------------------
Method used: hybrid urllib3 + Chrome capture + BeautifulSoup/regex.
Selenium was not used: per the instructor's September 7 note, a
Selenium-controlled browser is stuck in Cloudflare's verification loop.

Fetching. A urllib3 PoolManager (one for the whole run, with the user
agent above) fetches robots.txt and makes one probe request to the results
page. Grad Cafe is behind Cloudflare and answers scripted requests with
HTTP 403 (confirmed). The scraper therefore captures each page from a
Chrome window that a human has verified once: an AppleScript run through
subprocess tells Chrome to open the page URL in a new tab, waits for it to
load, returns document.documentElement.outerHTML, and closes the tab.

Pagination. Grad Cafe does not number pages; each page contains "next"
and "previous" links with a base64-encoded cursor. _find_next_url() uses
urllib.parse (urljoin, urlparse, parse_qs) to read each link's cursor,
decodes it (base64 -> JSON) and follows the one whose
_pointsToNextItems flag is true. 1,500 pages x 20 entries = 30,000.

Parsing. One applicant spans two or three <tr> rows: a main row (the one
containing the /result/<id> link) with university, program + degree, date
added and decision; a badge row (a div with class tw-flex-wrap) with the
term, American/International, and GPA / GRE / GRE V / GRE AW when given;
and an optional comment row (<p>). _parse_page() walks the rows and
attaches badge/comment rows to the applicant that precedes them.
BeautifulSoup finds rows and cells; regex splits "Accepted on Sep 11"
into decision and date and matches the term; string methods
(startswith/replace/strip) sort the badges into fields.

Fields per entry (16): program (raw "Program, University" text, kept for
traceability and for the LLM step), program_name, university, Degree,
comments, date_added, url, status (raw decision text), decision,
decision_date, term, US/International, GPA, GRE, GRE V, GRE AW.
Missing values are always the empty string "".

Resume. Every 10 pages the entries are written to applicant_data.json and
the next URL to progress.json (each written to a temporary file and then
renamed, so an interruption cannot leave a half-written file). Entries are
de-duplicated by URL as they are collected, so a restart from a stale
checkpoint cannot count a page twice. A crash or sleep loses at most 10
pages of work.

------------------------------------------------------------
5. Approach: cleaning (clean.py)
------------------------------------------------------------
clean_data() decodes HTML entities (html.unescape), removes any leftover
HTML tags, collapses whitespace, replaces None with "", and drops duplicate
URLs. Tag removal matches only real tags (</?[A-Za-z]...>), so comment text
such as "GPA < 3.5" is preserved; the comments were re-cleaned from the
original scrape after this rule was tightened. The raw fields program and
status are never altered.
Result on this dataset: 30,000 entries before and after (0 duplicates);
comments present in 13,926 entries, GPA in 18,108, GRE in 2,392,
GRE V in 2,006, GRE AW in 1,887; term and decision_date in all 30,000;
US/International in 29,461.

------------------------------------------------------------
6. Approach: LLM standardization
------------------------------------------------------------
The instructor's app.py (TinyLlama 1.1B via llama-cpp-python) was used
unmodified. Measured speed on this machine: about 3.4 s per row, which
would be ~28 hours for 30,000 rows. Two observations made a faster run
possible without changing the result:
  - only 12,065 of the 30,000 program strings are distinct, and
  - app.py decodes at temperature 0.0, so identical input strings share
    one result rather than separate model calls.
run_llm.py therefore standardizes each unique string once (two app.py
processes in parallel, 5 threads each, ~9 hours) and copies the result to
every row with that string. Every row receives the standardized values for
its program string, and every row keeps its own other fields.
llm_hosting/work/ holds app.py's per-string outputs (after app.py's own
post-processing).

Changes to the LLM-hosting files (app.py itself is unmodified):
  - added run_llm.py (parallel runner + merge, described above);
  - added postfix.py (second post-processing pass, below);
  - extended canon_universities.txt with 14 names (ETH Zurich, CUNY
    Graduate Center, EPFL, University at Buffalo (SUNY), Washington
    University in St. Louis, MIT Media Lab, KU Leuven, UC Santa Barbara,
    Icahn School of Medicine at Mount Sinai, and others);
  - extended canon_programs.txt with "Geological Sciences" and "German".

postfix.py rules (applied to every row, deterministic; a second run
changes 0 rows):
  - University: if the site's own university text already matches the
    canonical list, that canonical spelling is used; otherwise a table of
    known fixes, small connecting words lowered, acronyms restored from the
    site's text, and a close match against the canonical list.
  - Program: if the site's own program text already matches the canonical
    list, it is used; if the model's answer shares less than half its
    characters with the site's text (and the site's text is not an
    abbreviation), the site's text is kept; otherwise the model's answer.
  - Reproduction: from the included files, run_llm.py --merge followed by
    one postfix.py run regenerates llm_extend_applicant_data.json exactly.

Edge cases found and how they were handled:
  - app.py's post-processor title-cases every name before the canonical
    check, so acronyms came out as "Eth Zurich", "Cuny", "Nyu", "(Ucsb)",
    "Epfl", and small words as "At"/"And" ("Icahn School of Medicine At
    Mount Sinai", "Health And Kinesiology"). postfix.py restores acronyms
    from the original scraped university text, lowers connecting words,
    applies a table of known fixes, and re-checks the canonical list.
    In total postfix.py changed 5,014 rows.
  - Variants of one institution were not merged by the model ("Cuny" vs
    "Cuny Graduate Center", "Suny Buffalo", "Washu/Wustl"); mapped by
    postfix.py.
  - The model introduced a misspelling in 28 rows ("Lauhanne" for
    Lausanne) - a reminder that a small model can damage correct input;
    corrected.
  - The model truncated program names that contain commas at the comma
    (130 rows, e.g. "Black, Race, and Ethnic Studies" -> "Black"), because
    the combined input uses a comma as the program/university separator;
    it changed some meanings ("Comparative Literature" -> "Compare And
    Contrast Literature", 125 rows; "German" -> "Geometry", 11 rows) and
    occasionally answered in another language. All corrected by the
    program rules in postfix.py.
  - app.py's own fuzzy matcher (cutoff 0.84) mapped "Geological Sciences"
    to the nearest canonical program, "Biological Sciences" (11 rows);
    corrected by adding the name to canon_programs.txt.
  - Remaining imperfections: a few bare names ("Stanford", "Yale",
    "Princeton") were mapped; campus-in-parentheses forms such as
    "University of California (UCSB)" needed explicit mapping; and names
    without "University" in them (CEMFI, Weill Cornell Medicine,
    Michener Center for Writers) are correct as-is but would not be found
    by a naive filter.
  - The site's "GRE" badge holds values such as 163 or 170 (the 130-170
    section scale, apparently the quantitative score) rather than a
    260-340 total; the value is preserved exactly as displayed, and the
    separate "GRE V" and "GRE AW" badges are stored in their own fields.
  - 8 entries have an empty program_name because the site listed only a
    university for them; the raw "program" field still holds ", University".
  - 4 entries received "Unknown", app.py's value when it cannot identify
    a university; left as-is so the gap is visible rather than guessed.

------------------------------------------------------------
7. Known bugs / limitations
------------------------------------------------------------
  - The scraper depends on Google Chrome on macOS with "Allow JavaScript
    from Apple Events" enabled, and on a human completing Cloudflare's
    check once. On Linux/Windows the _fetch_with_chrome() helper would
    need an equivalent (Chrome remote debugging or Selenium where it works).
  - If Grad Cafe changes its HTML (class names, row layout), _parse_main_row
    and _parse_badge_row need updating.
  - The LLM step ran on an Intel-build Python under Rosetta (CPU only);
    a native Apple-Silicon build with Metal would be several times faster.
  - huggingface_hub 1.31.0 prints two deprecation warnings for arguments
    app.py passes to hf_hub_download; they are ignored and the model
    download completed with this version.

------------------------------------------------------------
8. Sources and assistance
------------------------------------------------------------
Course materials: Module 2 lecture and slides (urllib3, robots.txt,
BeautifulSoup, regex, string methods), the homework video, and the
assignment page including the instructor's September 7 note on the
Cloudflare workaround.
Documentation: urllib3 User Guide
(https://urllib3.readthedocs.io/en/stable/user-guide.html); Beautiful
Soup documentation; Python standard library docs (re, json, base64,
urllib.parse, urllib.robotparser, subprocess).
AI assistance: Claude (Anthropic) was used. All code was reviewed, run, and
tested by me.
No code was copied from other students, previous semesters, or solution
sites.