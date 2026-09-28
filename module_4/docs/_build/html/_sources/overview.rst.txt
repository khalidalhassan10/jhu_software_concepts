Overview and setup
==================

Requirements
------------

* Python 3.12
* PostgreSQL 16 or newer
* The packages in ``module_4/requirements.txt``:

  .. code-block:: bash

     pip install -r module_4/requirements.txt

Environment variables
---------------------

``DATABASE_URL`` (required)
   Where the application's database is. Nothing is hard-coded and there is no password prompt:

   .. code-block:: bash

      export DATABASE_URL="postgresql://postgres:PASSWORD@localhost:5432/gradcafe"

``TEST_DATABASE_URL`` (tests only)
   A separate database for the test suite. Its name **must end in** ``_test``: the tests empty
   the ``applicants`` table, so they refuse to run against any other database.

   .. code-block:: bash

      createdb -U postgres gradcafe_test
      export TEST_DATABASE_URL="postgresql://postgres:PASSWORD@localhost:5432/gradcafe_test"

   If ``TEST_DATABASE_URL`` is not set, the tests fall back to ``DATABASE_URL`` (this is how
   GitHub Actions runs them), still only if its name ends in ``_test``.

Create and load the database
----------------------------

.. code-block:: bash

   createdb -U postgres gradcafe
   cd module_4
   python -m src.load_data path/to/llm_extend_applicant_data.json

Running the loader again inserts nothing new: rows whose ``p_id`` already exists are skipped.

Run the application
-------------------

From ``module_4``, with ``DATABASE_URL`` set:

.. code-block:: bash

   flask --app src.flask_app:create_app run

Then open http://127.0.0.1:5000/analysis.

**Pull Data** reads the newest Grad Café pages. Grad Café sometimes refuses scripts (HTTP 403);
the scraper then reads pages through a Google Chrome window that is already open on
thegradcafe.com and has passed its verification.

Command-line scripts
--------------------

From ``module_4``:

``python -m src.query_data``
   Prints the eleven answers, computed in raw SQL.

``python -m src.orm_queries``
   Prints the same answers, computed through SQLAlchemy.

``python -m src.pull_data``
   Runs Pull Data without the web page.

Run the tests
-------------

From the repository root, with ``TEST_DATABASE_URL`` set:

.. code-block:: bash

   pytest module_4/tests -m "web or buttons or analysis or db or integration"

This runs the whole suite and fails unless coverage of ``module_4/src`` is 100%. See
:doc:`testing` for details.
