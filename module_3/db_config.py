"""Database settings shared by the loader, ORM, and Flask app."""
import os
from getpass import getpass


def settings(prompt=False):
    password = os.environ.get("PGPASSWORD")
    if password is None and prompt:
        password = getpass("PostgreSQL password: ")
    if password is None:
        raise RuntimeError("Set PGPASSWORD before running this program (see README.md).")
    return {
        "dbname": os.environ.get("PGDATABASE", "gradcafe"),
        "user": os.environ.get("PGUSER", "postgres"),
        "host": os.environ.get("PGHOST", "localhost"),
        "port": int(os.environ.get("PGPORT", "5432")),
        "password": password,
    }