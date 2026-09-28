Operational notes
=================

Busy-state policy
-----------------

Only one pull can run at a time. While it runs:

* ``POST /pull-data`` answers ``409 {"busy": true}`` and starts nothing;
* ``POST /update-analysis`` answers ``409 {"busy": true}`` and re-reads nothing;
* the page shows a notice, disables Pull Data, and reloads itself every 5 seconds.

The flag is released when the pull ends, whether it succeeded or failed.

Uniqueness key and idempotency
------------------------------

* ``p_id`` is the number at the end of each entry's URL
  (``https://www.thegradcafe.com/result/1020482`` → ``1020482``) and is the table's primary key.
* Every insert uses ``ON CONFLICT (p_id) DO NOTHING``, so loading or pulling the same entries
  twice stores them once. Running the loader again is safe.
* A pull inserts its whole batch in one transaction: if any row fails, none of that batch is kept.
* Records that are malformed (empty, not a dictionary, or without a numeric URL) are skipped.

Troubleshooting
---------------

``RuntimeError: DATABASE_URL is not set``
   Export it in the Terminal window you run from (see :doc:`overview`).

``Database tests need a database whose name ends in _test``
   Set ``TEST_DATABASE_URL`` to your test database. This protects your real data.

``password authentication failed``
   The password inside the URL is wrong. Check it with ``psql "$DATABASE_URL" -c "SELECT 1"``.

``ModuleNotFoundError: No module named 'src'``
   Run the app and scripts from ``module_4``, and pytest from the repository root.

Tests error with ``fixture 'client' not found``
   ``tests/conftest.py`` is missing or misnamed; the name must be exactly ``conftest.py``.

Coverage below 100%
   The report's ``Missing`` column lists the line numbers no test executed.

Pull Data fails with HTTP 403 or a verification page
   Open thegradcafe.com in Google Chrome, pass its check, keep the window open, and pull again.

GitHub Actions run is red
   Open the failing step's log. The usual causes are a package missing from
   ``requirements.txt`` or a test that relied on local data.
