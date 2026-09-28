API reference
=============

Flask application and routes
----------------------------

The routes are created inside :func:`src.flask_app.create_app`:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Route
     - Behaviour
   * - ``GET /``
     - Redirects (302) to ``/analysis``.
   * - ``GET /analysis``
     - The analysis page: every answer labelled ``Answer:``, both buttons, and a message for
       each state (pull running, last pull result, database unreachable).
   * - ``POST /pull-data``
     - Starts a pull. ``202 {"ok": true}`` when it runs in the background;
       ``200 {"ok": true, "inserted": n}`` when it runs synchronously;
       ``500 {"ok": false, "error": ...}`` if it fails;
       ``409 {"busy": true}`` if a pull is already running.
   * - ``POST /update-analysis``
     - Re-reads the database: ``200 {"ok": true}``; ``500`` if the query fails;
       ``409 {"busy": true}`` while a pull is running (nothing is re-read).

.. automodule:: src.flask_app

scrape.py
---------

.. automodule:: src.scrape

clean.py
--------

.. automodule:: src.clean

pull_data.py
------------

.. automodule:: src.pull_data

load_data.py
------------

.. automodule:: src.load_data

query_data.py
-------------

.. automodule:: src.query_data

models.py
---------

.. automodule:: src.models
   :exclude-members: metadata, registry, _sa_registry, _sa_class_manager

orm_queries.py
--------------

.. automodule:: src.orm_queries

db_config.py
------------

.. automodule:: src.db_config
