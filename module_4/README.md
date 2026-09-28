Grad Café Analytics (Module 4: Testing and Documentation)
=========================================================

A Flask service that stores Grad Café admission results in PostgreSQL and shows an analysis
page with two actions: **Pull Data** (fetch new entries from Grad Café) and **Update Analysis**
(re-read the database). Module 4 adds a full pytest suite with 100% coverage, a GitHub Actions
workflow, and Sphinx documentation.

* **Documentation (Read the Docs):** https://jhu-software-concepts-khaled.readthedocs.io/en/latest/
* **Repository (SSH):** `git@github.com:khalidalhassan10/jhu_software_concepts.git`
* **CI proof:** `actions_success.png` (workflow: `.github/workflows/tests.yml`)
* **Coverage proof:** `coverage_summary.txt`


Folder layout
-------------

```text
jhu_software_concepts/
├── .github/workflows/tests.yml     GitHub Actions workflow (the one GitHub runs)
├── .readthedocs.yaml               Read the Docs build settings
└── module_4/
    ├── src/                        application code (Flask, ETL, database)
    ├── tests/                      all tests (conftest.py holds the shared fixtures)
    ├── docs/                       Sphinx source; built HTML in docs/_build/html
    ├── .github/workflows/tests.yml copy of the workflow, for submission
    ├── pytest.ini
    ├── requirements.txt
    ├── coverage_summary.txt
    ├── actions_success.png
    └── README.md
```


Setup
-----

Requirements: Python 3.12 and PostgreSQL 16 or newer.

```bash
pip install -r module_4/requirements.txt
createdb -U postgres gradcafe
createdb -U postgres gradcafe_test
```

The application reads its database from `DATABASE_URL`; nothing is hard-coded and there is no
password prompt. The tests use a separate database whose name must end in `_test`, because they
empty the `applicants` table between tests.

```bash
export DATABASE_URL="postgresql://postgres:PASSWORD@localhost:5432/gradcafe"
export TEST_DATABASE_URL="postgresql://postgres:PASSWORD@localhost:5432/gradcafe_test"
```

Replace `PASSWORD` with your own PostgreSQL password. Never commit a real password.


Load the data
-------------

From `module_4`, load the cleaned Module 2/3 data (the JSON file is kept in `module_3`):

```bash
cd module_4
python -m src.load_data ../module_3/llm_extend_applicant_data.json
```

Running it again inserts nothing new: rows whose `p_id` already exists are skipped.


Run the application
-------------------

From `module_4`, with `DATABASE_URL` set:

```bash
flask --app src.flask_app:create_app run
```

Open http://127.0.0.1:5000/analysis.

* **Update Analysis** re-reads the database and refreshes the answers.
* **Pull Data** fetches Grad Café entries newer than the database. If Grad Café refuses scripts
  (HTTP 403), pages are read through a Google Chrome window that is already open on
  thegradcafe.com and has passed its verification.
* While a pull runs, both buttons answer `409 {"busy": true}` and the page says data is
  being retrieved.

Command-line versions of the analysis, from `module_4`: `python -m src.query_data` (raw SQL)
and `python -m src.orm_queries` (SQLAlchemy).


Run the tests
-------------

From the repository root, with `TEST_DATABASE_URL` set:

```bash
pytest module_4/tests -m "web or buttons or analysis or db or integration"
```

This runs all 85 tests and fails unless coverage of `module_4/src` is 100% (set in `pytest.ini`).
Every test carries one or more of the five markers, so this command selects the whole suite.

| Marker | Tests |
|---|---|
| `web` | app factory, routes, page HTML (`test_flask_page.py`) |
| `buttons` | Pull Data / Update Analysis, busy gating, the pull pipeline (`test_buttons.py`, `test_pull_pipeline.py`) |
| `analysis` | `Answer:` labels, two-decimal percentages (`test_analysis_format.py`) |
| `db` | inserts, schema, uniqueness, queries (`test_db_insert.py`, `test_queries.py`) |
| `integration` | pull → update → render (`test_integration_end_to_end.py`) |

The tests never use the internet: the scraper, the loader and the query can be replaced with
fakes through `create_app(...)`, and network calls are replaced with `monkeypatch`.

GitHub Actions runs the same command on every push, with its own temporary PostgreSQL
(`.github/workflows/tests.yml`).


Documentation
-------------

Published: https://jhu-software-concepts-khaled.readthedocs.io/en/latest/

Pages: overview and setup, architecture (web, ETL and database layers), API reference (autodoc),
testing guide, and operational notes. To build it locally, from `module_4`:

```bash
sphinx-build -b html docs docs/_build/html
open docs/_build/html/index.html
```


Changes from Module 3
---------------------

* All code moved to `src/`; `app.py` became `flask_app.py` with a `create_app(...)` factory that
  accepts a scraper, loader, query and database URL, so tests can inject fakes.
* The database location comes only from `DATABASE_URL` (no hard-coded defaults or prompts).
* `load_data.py` and `query_data.py` are import-safe functions; malformed records are skipped,
  and a failed batch is rolled back with no partial writes.
* Empty or brand-new databases show `n/a` instead of crashing.
* The routes are `GET /analysis`, `POST /pull-data` and `POST /update-analysis`, answering JSON.
* The page labels every answer `Answer:`, has `data-testid` selectors, and shows a message for
  every state.
* `scrape.py` and `clean.py` keep only what Pull Data uses; the Module 2 bulk scraper and the
  LLM step stay in earlier modules.


AI assistance
-------------

Claude (Anthropic) was used.