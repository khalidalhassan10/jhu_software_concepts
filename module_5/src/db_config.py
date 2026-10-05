"""Database settings: where PostgreSQL is, and the row limits every query uses.

The connection comes from the environment, never from the code: either DATABASE_URL,
or the five variables DB_HOST, DB_PORT, DB_NAME, DB_USER and DB_PASSWORD.
"""


import os
from urllib.parse import quote

DEFAULT_LIMIT = 20
MAX_LIMIT = 100
DB_VARIABLES = ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD")


def url_from_parts(environ):
    """Build ``postgresql://user:password@host:port/name`` from the five DB_* variables.

    :param environ: the environment, e.g. ``os.environ``.
    :returns: the connection URL.
    :raises RuntimeError: if any of the five variables is missing or empty.
    """
    missing = [name for name in DB_VARIABLES if not environ.get(name)]
    if missing:
        raise RuntimeError(
            "Database settings are missing. Set DATABASE_URL, or all of "
            f"{', '.join(DB_VARIABLES)} (missing: {', '.join(missing)})."
        )
    user = quote(environ["DB_USER"], safe="")
    password = quote(environ["DB_PASSWORD"], safe="")
    return (
        f"postgresql://{user}:{password}@{environ['DB_HOST']}:"
        f"{environ['DB_PORT']}/{environ['DB_NAME']}"
    )


def get_database_url(database_url=None):
    """Return the PostgreSQL connection URL to use.

    Order: the argument (tests pass one), then DATABASE_URL, then the five DB_* variables.

    :param database_url: optional URL that overrides the environment.
    :returns: a URL such as ``postgresql://gradcafe_app:PASSWORD@localhost:5432/gradcafe``.
    :raises RuntimeError: if nothing is set.
    """
    return database_url or os.environ.get("DATABASE_URL") or url_from_parts(os.environ)


def clamp_limit(value, default=DEFAULT_LIMIT, maximum=MAX_LIMIT):
    """Turn any requested row limit into a safe whole number from 1 to ``maximum``.

    :param value: the requested limit, e.g. text typed in a web address.
    :param default: used when ``value`` is not a whole number.
    :param maximum: the largest limit allowed.
    :returns: an int from 1 to ``maximum``.
    """
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(1, min(maximum, number))
