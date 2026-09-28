"""SQLAlchemy model for the existing applicants table."""

# ---- Block 1: imports ----
from datetime import date

from sqlalchemy import Date, Float, Integer, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from src.db_config import get_database_url      # M4 CHANGE: "src." prefix, and DATABASE_URL instead of settings()


# ---- Block 2: the base class every model inherits from ----
class Base(DeclarativeBase):
    pass


# ---- Block 3: the applicants table as a Python class (UNCHANGED from Module 3) ----
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


# ---- Block 4: M4 CHANGE - the engine now comes from DATABASE_URL ----
# SQLAlchemy needs to be told which driver to use: "postgresql://" -> "postgresql+psycopg://"
# (psycopg = the same library load_data.py uses). psycopg itself accepts the plain URL.
def sqlalchemy_url(database_url):
    """Turn ``postgresql://...`` into ``postgresql+psycopg://...`` for SQLAlchemy.

    :param database_url: a PostgreSQL URL.
    :returns: the same URL with the psycopg driver named.
    """
    return database_url.replace("postgresql://", "postgresql+psycopg://", 1)   # 1 = only the first match


# create_engine does NOT connect yet; it connects when a Session first asks for data.
def create_session_factory(database_url=None):
    """Return a sessionmaker bound to the database.

    :param database_url: optional URL overriding DATABASE_URL (tests pass their test database here).
    :returns: a ``sessionmaker``; call it (``Session()``) to open a session.
    """
    engine = create_engine(
        sqlalchemy_url(get_database_url(database_url)),   # passed-in URL, else DATABASE_URL
        pool_pre_ping=True,                                # check the connection is alive before using it
    )
    return sessionmaker(bind=engine)