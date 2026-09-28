"""Database settings: where PostgreSQL is, read from the DATABASE_URL environment variable."""


import os


def get_database_url(database_url=None):
    """Return the PostgreSQL connection URL to use.

    :param database_url: optional URL that overrides the environment (used by tests).
    :returns: a URL such as ``postgresql://postgres:PASSWORD@localhost:5432/gradcafe``.
    :raises RuntimeError: if no URL was passed and DATABASE_URL is not set.
    """
    url = database_url or os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. Example: "
            'export DATABASE_URL="postgresql://postgres:PASSWORD@localhost:5432/gradcafe"'
        )
    return url
