# Module 3: Grad Café Database Analysis

## Overview

This project uses the Grad Café entries I collected and cleaned for Module 2. I loaded them into one PostgreSQL table called `applicants`, answered 11 questions with SQL, repeated the analyses with SQLAlchemy, and displayed the results on a Flask webpage.

The webpage has two buttons. **Pull Data** checks recent Grad Café pages and inserts entries that are not already in the database. **Update Analysis** reads the database again and displays its latest committed results without starting a scrape.

## Data and project files

The initial database load came from `llm_extend_applicant_data.json`, which contains 30,000 cleaned Module 2 entries and their LLM-generated program and university fields. `applicant_data.json` contains the cleaned entries before the LLM fields were added.

| File | Purpose |
| --- | --- |
| `load_data.py` | Creates the `applicants` table if needed and imports the cleaned JSON with psycopg. |
| `query_data.py` | Answers Questions 1–11 with SQL. |
| `models.py` | Maps the existing table to a SQLAlchemy `Applicant` class. |
| `orm_queries.py` | Answers the questions through SQLAlchemy. |
| `db_config.py` | Provides connection settings to SQLAlchemy and the Pull Data worker. |
| `app.py` | Runs the Flask webpage. |
| `templates/analysis.html` | Displays the questions, results, buttons, and status messages. |
| `static/style.css` | Styles the webpage. |
| `pull_data.py` | Uses the Module 2 scraper and cleaner to add recent entries. |
| `scrape.py`, `clean.py` | Module 2 scraping and cleaning code reused by Pull Data. |
| `llm_hosting/` | The Module 2 local LLM standardization files (the instructor-provided tool and my Module 2 additions). |
| `query_results.pdf` | Questions, SQL queries, results, and explanations. |
| `limitations.pdf` | Two paragraphs about the limits of this self-reported dataset. |
| `screenshots/` | SQL console output, ORM console output, and the running webpage. |
| `github.txt` | SSH URL of the private GitHub repository. |

## Requirements and setup

I ran the project on macOS with Python 3.12, PostgreSQL 18, psycopg 3, SQLAlchemy 2, Flask, Beautiful Soup, and urllib3. The database is named `gradcafe`, and the connection defaults to the `postgres` user on `localhost:5432`. SQLAlchemy and Pull Data support connection overrides through the `PGDATABASE`, `PGUSER`, `PGHOST`, and `PGPORT` environment variables. The `load_data.py` and `query_data.py` scripts use the connection settings written in those files. All components must connect to the same database.

From the `module_3` folder, create the Conda environment if it does not already exist:

```bash
conda create -n py312 python=3.12
```

Then activate the environment and install the dependencies:

```bash
conda activate py312
python -m pip install -r requirements.txt
```

First-time setup: install PostgreSQL (I used the EDB installer for macOS), then create the database and put the password in the environment for this Terminal session. The password is typed without being displayed and is never stored in a project file:

```bash
createdb -U postgres gradcafe
read -s PGPASSWORD
export PGPASSWORD
```

Then load the data and run the console analyses:

```bash
python load_data.py
python query_data.py
python orm_queries.py
```

`load_data.py` and `query_data.py` prompt for the PostgreSQL password; `orm_queries.py` uses `PGPASSWORD` if it is set and prompts otherwise. The loader uses `ON CONFLICT (p_id) DO NOTHING`, so running it again does not replace or duplicate rows that are already present.

Flask and its separate Pull Data process need `PGPASSWORD` in the Terminal environment (set above):

```bash
python app.py
```

Then open `http://127.0.0.1:5000/`. The password is not included in the source code, screenshots, or submission.

## How the webpage updates data

The page calculates its results with the SQLAlchemy `Applicant` model each time it loads. **Update Analysis** opens a database session and runs the queries again. It does not contact Grad Café or start a scrape. If a pull is running, the page says so and shows the latest committed results.

**Pull Data** starts a separate process and prevents another pull from starting while one is active. It reuses the Module 2 robots.txt check, page fetching, parser, pagination, and `clean_data()` function. It begins at the newest results page because the Module 2 scraper's saved progress points to older pages and its original 30,000-entry target has already been met. The worker inserts cleaned entries using their result IDs and `ON CONFLICT (p_id) DO NOTHING`, so it does not overwrite existing applicants, and it stops after two consecutive pages with no new entries.

If Grad Café blocks direct requests with HTTP 403, the Module 2 scraper may require an open Google Chrome window where the site has been verified. The site can also change or become unavailable, so a future pull is not guaranteed to find the same entries.

Pull Data does **not** run the Module 2 LLM on newly scraped entries. Their `llm_generated_program` and `llm_generated_university` columns are therefore NULL. This is important when interpreting Question 9: a newly pulled entry can match the original-field query before it can match the LLM-field query.

## Results and verification

The original Module 2 import contained 30,000 entries. In my test, Pull Data added **8 new entries from 3 pages**, making 30,008 entries in the database. I then used Update Analysis and reran both console programs.

| Result | Before Pull Data | After Pull Data and Update Analysis |
| --- | ---: | ---: |
| Q1: Fall 2026 entries | 29,577 | 29,582 |
| Q2: International percentage | 46.33% | 46.32% |

The other **formatted** results remained the same in this test. For example, Question 8 counted 28 accepted Fall 2026 Computer Science PhD entries at the four specified universities using original fields. Question 9 counted 32 using the LLM-generated fields, a difference of +4. For my original Question 10, 569 of 1,679 Fall 2026 Computer Science entries were Masters (33.89%), and 1,109 were PhD (66.05%). Question 11 found average reported GPAs of 3.85 among 280 accepted entries and 3.74 among 122 rejected entries, a difference of +0.11.

I ran `query_data.py` and `orm_queries.py` again after the pull and checked that their displayed answers agreed. I also confirmed that the Flask page displayed the updated Q1 and Q2 values. The before and after figures document this particular test; Grad Café can receive more submissions, so a later pull may produce different results. Running only `load_data.py` on a fresh database reproduces the original JSON import, not the eight entries fetched later.

The averages reflect submitted values. In particular, the displayed GRE Quantitative average of 259.90 and GRE Analytical Writing average of 8.34 are implausible and indicate data-quality problems. I did not silently change the stored scores to make the averages look more plausible. `limitations.pdf` explains why these entries should not be treated as a representative sample of all graduate applicants.

## Raw SQL compared with SQLAlchemy

For Question 1, my raw SQL query in `query_data.py` is:

```sql
SELECT COUNT(term)
FROM applicants
WHERE term ILIKE 'Fall 2026';
```

The corresponding SQLAlchemy query in `orm_queries.py` uses `A = Applicant`:

```python
session.scalar(
    select(func.count())
    .select_from(A)
    .where(A.term.ilike("Fall 2026"))
)
```

Both queries count Fall 2026 entries. `COUNT(term)` and `COUNT(*)` give the same answer here because a NULL term cannot satisfy the Fall 2026 condition. Raw SQL is shorter and makes the PostgreSQL operation easy to inspect directly. SQLAlchemy uses the `Applicant` model, making it easier to reuse the same approach for database reads in Flask. Raw SQL gives me direct control over a query, while the ORM helps organize it with the rest of my Python code.

## Resources and assistance

- The EN.605.256 Module 2 and Module 3 assignments, lecture materials, and the instructor-provided Module 2 LLM standardizer informed the project requirements and original data workflow.
- The application entries came from [Grad Café's survey pages](https://www.thegradcafe.com/survey/). The Module 2 submission describes how the data was collected and cleaned.
- I referred to the [SQLAlchemy 2.0 ORM Quick Start](https://docs.sqlalchemy.org/en/20/orm/quickstart.html), [Flask Quickstart](https://flask.palletsprojects.com/en/stable/quickstart/), and [psycopg 3 documentation](https://www.psycopg.org/psycopg3/docs/basic/usage.html) for the database and webpage work.
- **AI assistance:** ChatGPT (OpenAI) and Claude (Anthropic) were used. 

## Submission

`module_3.zip` contains this folder: the code, the JSON data needed to run it, both PDFs, the three screenshots, and `github.txt` with the SSH URL of the private repository. The repository and the ZIP contain the same final version. No PostgreSQL password, `.env` file, virtual environment, `__pycache__`, or downloaded LLM model weights are included.