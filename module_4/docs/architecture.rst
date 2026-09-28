Architecture
============

The service separates web, ETL, and database responsibilities. The web layer coordinates
scraping and loading for Pull Data, and calls the database query functions directly to build
the analysis for the page and for Update Analysis.

.. code-block:: text

   Browser
      |  GET /analysis, POST /pull-data, POST /update-analysis
      v
   Web layer ........ flask_app.py (+ templates/, static/)
      |                                     |
      | Pull Data                           | page and Update Analysis
      v                                     |
   ETL layer ........ pull_data.py          |
                      -> scrape.py          |
                      -> clean.py           |
      |                                     |
      v  new rows                           v  analysis
   Database layer ... load_data.py (writes)   models.py + orm_queries.py (reads)
                      db_config.py (DATABASE_URL)       query_data.py (raw SQL, command line)
      |
      v
   PostgreSQL: one table, ``applicants``

Web layer
---------

:mod:`src.flask_app` builds the application with :func:`src.flask_app.create_app`. The factory
receives three functions, so tests can replace any of them with a fake:

* ``scraper()`` returns new Grad Café entries (default: the live pull pipeline);
* ``loader(rows)`` stores them and returns how many were new (default: :func:`src.load_data.insert_rows`);
* ``query()`` returns the analysis dictionary (default: :func:`src.orm_queries.run_analyses`).

A :class:`src.flask_app.PullState` object holds the busy flag, the last pull's result and the
latest analysis. :func:`src.flask_app.format_analysis` turns the analysis into the labelled,
formatted answers the page shows.

ETL layer (extract, transform, load)
------------------------------------

* **Extract**: :mod:`src.scrape` checks ``robots.txt``, fetches pages (urllib3, or Chrome
  after an HTTP 403), parses each page with BeautifulSoup and finds the next page's link.
  :func:`src.pull_data.scrape_new` walks the pages from newest to oldest and keeps only
  entries whose ``p_id`` is not in the database yet.
* **Transform**: :func:`src.clean.clean_data` removes leftover HTML, decodes entities, trims
  whitespace and drops duplicate entries.
* **Load**: :func:`src.load_data.insert_rows` converts every value (text, number, date, NULL)
  and inserts the batch in one transaction.

Database layer
--------------

* One table, ``applicants``, with the 15 required Module 3 columns. ``p_id`` (the number at the
  end of the entry's URL) is the primary key.
* :mod:`src.db_config` is the only place that knows where the database is (``DATABASE_URL``).
* Writes use psycopg (:mod:`src.load_data`). Reads for the page use SQLAlchemy
  (:mod:`src.models`, :mod:`src.orm_queries`). :mod:`src.query_data` answers the same questions
  in raw SQL for the command line.
