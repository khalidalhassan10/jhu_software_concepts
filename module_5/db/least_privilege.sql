-- Least-privilege PostgreSQL user for the Grad Café app (Module 5, Step 3).
--
-- Run once as the table's owner (postgres), from module_5:
--     psql "$DATABASE_URL" -f db/least_privilege.sql
-- Then give the user a password (it is typed, never stored in this file):
--     psql "$DATABASE_URL" -c "\password gradcafe_app"
--
-- The app only reads rows (the analysis page, the search) and adds rows (Pull Data),
-- so it gets exactly SELECT and INSERT on the one table, and nothing else.

CREATE ROLE gradcafe_app
    LOGIN
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOREPLICATION
    NOBYPASSRLS;

-- PostgreSQL gives PUBLIC (every role) CONNECT and TEMPORARY on a new database by default.
-- Remove those defaults on gradcafe, so only roles granted CONNECT below can connect to it,
-- and gradcafe_app cannot create even temporary tables there.
REVOKE ALL ON DATABASE gradcafe FROM PUBLIC;

GRANT CONNECT ON DATABASE gradcafe TO gradcafe_app;
GRANT USAGE ON SCHEMA public TO gradcafe_app;
GRANT SELECT, INSERT ON TABLE applicants TO gradcafe_app;