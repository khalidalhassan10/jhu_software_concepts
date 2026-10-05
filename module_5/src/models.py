"""SQLAlchemy model for the existing applicants table."""


from datetime import date

from sqlalchemy import Date, Float, Integer, Text, create_engine, inspect
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from src.db_config import get_database_url


class Base(DeclarativeBase):
    """Parent class of every SQLAlchemy model in this project."""
    def column_names(self):
        """Return this model's table column names, in table order."""
        return [column.key for column in inspect(type(self)).columns]

    def as_dict(self):
        """Return this row as a plain dictionary of column name -> value."""
        return {name: getattr(self, name) for name in self.column_names()}


class Applicant(Base):
    """One row of the ``applicants`` table (the Module 3 schema, unchanged)."""

    __tablename__ = "applicants"

    p_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program: Mapped[str | None] = mapped_column(Text)
    comments: Mapped[str | None] = mapped_column(Text)
    date_added: Mapped[date | None] = mapped_column(Date)
    url: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(Text)
    term: Mapped[str | None] = mapped_column(Text)
    us_or_international: Mapped[str | None] = mapped_column(Text)
    gpa: Mapped[float | None] = mapped_column(Float)
    gre: Mapped[float | None] = mapped_column(Float)
    gre_v: Mapped[float | None] = mapped_column(Float)
    gre_aw: Mapped[float | None] = mapped_column(Float)
    degree: Mapped[str | None] = mapped_column(Text)
    llm_generated_program: Mapped[str | None] = mapped_column(Text)
    llm_generated_university: Mapped[str | None] = mapped_column(Text)


def sqlalchemy_url(database_url):
    """Turn ``postgresql://...`` into ``postgresql+psycopg://...`` for SQLAlchemy.

    :param database_url: a PostgreSQL URL.
    :returns: the same URL with the psycopg driver named.
    """
    return database_url.replace("postgresql://", "postgresql+psycopg://", 1)


def create_session_factory(database_url=None):
    """Return a sessionmaker bound to the database.

    :param database_url: optional URL overriding DATABASE_URL (tests pass their test database here).
    :returns: a ``sessionmaker``; call it (``Session()``) to open a session.
    """
    engine = create_engine(
        sqlalchemy_url(get_database_url(database_url)),
        pool_pre_ping=True,
    )
    return sessionmaker(bind=engine)
