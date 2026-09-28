Testing guide
=============

Running the tests
-----------------

From the repository root, with ``TEST_DATABASE_URL`` pointing at a database whose name ends in
``_test`` (see :doc:`overview`):

.. code-block:: bash

   pytest module_4/tests -m "web or buttons or analysis or db or integration"

``pytest.ini`` adds coverage automatically: the run fails unless every line of ``module_4/src``
is executed (``--cov-fail-under=100``). While writing a test, add ``--no-cov`` to skip that check.

Markers
-------

Every test carries at least one marker, and the command above selects all five, so it runs
the whole suite. Run one group with ``-m``, for example ``pytest module_4/tests -m db``.

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Marker
     - What it covers
   * - ``web``
     - The app factory, routes, and the page's HTML (``test_flask_page.py``)
   * - ``buttons``
     - Pull Data / Update Analysis, busy gating, and the pull pipeline (``test_buttons.py``,
       ``test_pull_pipeline.py``)
   * - ``analysis``
     - ``Answer:`` labels and two-decimal percentages (``test_analysis_format.py``)
   * - ``db``
     - Inserts, schema, uniqueness, queries (``test_db_insert.py``, ``test_queries.py``)
   * - ``integration``
     - Pull, update and render end to end (``test_integration_end_to_end.py``)

Stable selectors
----------------

Tests find page elements by ``data-testid``, never by position or styling:

* ``pull-data-btn`` and ``update-analysis-btn``: the two buttons;
* ``analysis-item``: one answer card (``.label`` = question, ``.value`` = ``Answer: ...``);
* ``busy-notice``, ``pull-notice``, ``error-notice``: the status messages.

Fixtures and test doubles (``tests/conftest.py``)
--------------------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Fixture
     - What it provides
   * - ``fake_query``
     - Returns fixed analysis values and counts its calls (``fake_query.calls``), so a test can
       prove that a busy Update Analysis re-read nothing.
   * - ``fake_scraper``
     - Returns two fixed entries instantly: no internet.
   * - ``recording_loader``
     - Stores nothing; remembers the rows it received (``recording_loader.calls``).
   * - ``app`` / ``client``
     - The app built with the three fakes, and its Flask test client (no browser, no server).
   * - ``database_url``
     - The test database URL; refuses any name not ending in ``_test``.
   * - ``clean_db``
     - Empties ``applicants`` before and after each test.
   * - ``db_app`` / ``db_client``
     - The app with a fake scraper but the real loader and query, on the empty test database.
   * - ``make_row`` / ``db_rows``
     - Build realistic scraped records for database tests.

Busy state without ``sleep()``
------------------------------

Tests never wait for a real pull. They set ``app.config["PULL_STATE"].busy = True`` directly
and check that both buttons answer ``409 {"busy": true}``. The one background-thread test waits
on a ``threading.Event`` that the fake loader sets, which returns the moment the pull finishes.

No live internet
----------------

Network calls in ``scrape.py`` and ``pull_data.py`` (urllib3, Chrome, ``robots.txt``, the
politeness pause) are replaced with ``monkeypatch``, and Grad Café pages are small HTML strings
written in the tests.
