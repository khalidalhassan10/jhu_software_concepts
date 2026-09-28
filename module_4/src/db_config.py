"""Database settings: where PostgreSQL is, read from the DATABASE_URL environment variable."""

# ---- Block 1: imports ----
import os                                # os.environ = the environment variables of your Terminal


# ---- Block 2: the one function every other file uses to find the database ----
# Order of preference:
#   1. a URL passed in directly (tests pass a test-database URL this way = "tests may override")
#   2. the DATABASE_URL environment variable (how you run the app normally)
# No password prompt: tests and GitHub Actions cannot type a password.
def get_database_url(database_url=None):
    """Return the PostgreSQL connection URL to use.

    :param database_url: optional URL that overrides the environment (used by tests).
    :returns: a URL such as ``postgresql://postgres:PASSWORD@localhost:5432/gradcafe``.
    :raises RuntimeError: if no URL was passed and DATABASE_URL is not set.
    """
    url = database_url or os.environ.get("DATABASE_URL")     # passed-in URL wins; else the environment
    if not url:                                              # neither exists -> stop with a clear message
        raise RuntimeError(
            "DATABASE_URL is not set. Example: "
            'export DATABASE_URL="postgresql://postgres:PASSWORD@localhost:5432/gradcafe"'
        )
    return url