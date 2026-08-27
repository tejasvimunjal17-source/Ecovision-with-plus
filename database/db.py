"""
database/db.py
----------------
PHASE 2B — PostgreSQL (Supabase) access layer, replacing SQLite.

DESIGN GOAL (unchanged from before this phase): every caller in this
codebase — backend/auth.py, backend/complaints.py, backend/analytics.py,
chatbot/prakriti.py, and several pages/*.py files — talks to this module
through exactly four functions:

    get_connection()   -- context manager yielding a raw connection
    execute(query, params)     -- INSERT/UPDATE/DELETE, returns new row id or None
    fetch_one(query, params)   -- SELECT ... LIMIT-1-shaped, returns dict or None
    fetch_all(query, params)   -- SELECT, returns list[dict]

Every one of those four function signatures is UNCHANGED. Every
existing caller's raw SQL string is UNCHANGED (with the seven narrow,
individually-documented exceptions listed in supabase/README.md's
"What changed in caller files, and why" section — all vendor-specific
SQLite function calls, like datetime('now') or julianday(), which have
no generic string-substitution equivalent in PostgreSQL). This module
is where 100% of the SQLite -> PostgreSQL translation work happens, so
nothing else in the app has to change to keep working.

WHY psycopg2 (a direct Postgres connection), NOT the supabase-py /
postgrest REST client
--------------------------------------------------------------------------
Every caller passes a raw, hand-written parameterized SQL string --
that's the entire existing query style throughout this codebase.
Supabase's REST API (what the `supabase-py` SDK talks to, authenticated
via SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY) has no "run this raw SQL
string" endpoint -- it only offers a fluent table/filter builder
(`.table("x").select("y").eq("z", 1)`), which cannot represent this
codebase's joins, GROUP BY aggregates, or CASE expressions without
rewriting every single query in every caller file. That would violate
the explicit "keep existing function names and caller-facing behavior"
requirement and scatter Supabase-specific query-building logic across
backend/, chatbot/, and pages/ instead of containing it here.

A direct Postgres connection (via psycopg2, using SUPABASE_DB_URL --
the connection string from Supabase's dashboard under Project Settings
-> Database, NOT the REST API URL) lets every existing raw SQL string
keep running almost completely unchanged. See config/settings.py's
SUPABASE_DB_URL / SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY comments for
the full split of what each credential is actually used for.

WHAT THIS MODULE TRANSLATES AUTOMATICALLY (so callers don't have to)
--------------------------------------------------------------------------
1. Placeholder syntax: SQLite's "?" -> psycopg2's "%s". A plain
   query.replace("?", "%s") is used -- verified safe for this specific,
   fully-enumerated codebase because no existing query string contains a
   literal "?" character inside a quoted value (confirmed by reading
   every INSERT/SELECT/UPDATE/DELETE string in backend/, chatbot/, and
   pages/ during the Phase 2A audit). This is NOT a generically-safe
   transformation for arbitrary future SQL -- if a future query needs a
   literal "?" in a string value, it must be written with "%s" directly
   and passed through unchanged (this replace is a no-op on strings that
   don't contain a bare "?").

2. "INSERT OR IGNORE INTO" -> "INSERT INTO ... ON CONFLICT DO NOTHING".
   SQLite's OR IGNORE has no direct PostgreSQL keyword; "ON CONFLICT DO
   NOTHING" with NO conflict target specified is PostgreSQL's generic
   equivalent -- it silently skips the row if ANY unique/exclusion
   constraint would be violated, exactly matching OR IGNORE's semantics.
   Currently used by exactly one live, unmodified caller:
   pages/8_Admin_Dashboard.py's "Add Category" form.

3. Auto-appended "RETURNING id" on INSERT statements (that don't already
   have a RETURNING clause), so execute()'s return value keeps meaning
   "the new row's id" -- matching sqlite3's cur.lastrowid, which
   PostgreSQL has no equivalent attribute for. Every table in this
   schema names its primary key "id" (verified against every migration
   in supabase/migrations/), so this is safe. If the INSERT was skipped
   by ON CONFLICT DO NOTHING, RETURNING yields zero rows and execute()
   returns None instead of raising -- callers that don't use the return
   value (the one OR IGNORE caller above) are unaffected either way.

WHAT THIS MODULE DELIBERATELY DOES NOT TRANSLATE
--------------------------------------------------------------------------
Vendor-specific SQL *functions* embedded inside a handful of query
strings (datetime('now'), julianday(), strftime(), date()) have NO safe
generic string-substitution equivalent -- e.g. translating a julianday()
difference into EXTRACT(EPOCH FROM ...) is a structural rewrite of the
expression, not a token swap, and attempting it generically here would
be exactly the kind of "blind string replacement" this phase's
instructions explicitly warned against. Those seven occurrences were
instead fixed directly, one at a time, at their three call sites
(backend/auth.py, backend/complaints.py, backend/analytics.py) -- see
supabase/README.md for the full list of exactly which lines changed and
why. Every changed line preserves its function's existing name,
signature, and return shape.

WHAT init_db() DOES NOW (very different from before)
--------------------------------------------------------------------------
Table creation and reference-data seeding are no longer performed by
the running Streamlit app at all -- they live entirely in
supabase/migrations/*.sql, applied ONCE via the Supabase SQL Editor or
CLI (see supabase/README.md). init_db() is now a lightweight
readiness/connectivity check only: it confirms SUPABASE_DB_URL is
configured and that a connection can actually be opened, raising a
clear ConfigurationError immediately (caught and shown via st.error() at
both existing call sites -- app.py and utils/helpers.py -- with no
change to either call site's function signature or call shape) rather
than letting a confusing failure surface later on the first real query.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager

import psycopg2
import psycopg2.extras

from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ecovision.db")


class ConfigurationError(Exception):
    """Raised when EcoVision AI cannot reach its database because
    SUPABASE_DB_URL is missing/placeholder, or the connection itself
    fails -- deliberately a distinct, clearly-named exception type so
    call sites can show a clear "fix your configuration" message
    instead of a raw psycopg2 traceback (see app.py / utils/helpers.py)."""


@contextmanager
def get_connection():
    """Yield a raw psycopg2 connection, dict-row cursor factory (mirrors
    the previous sqlite3 conn.row_factory behavior), commit on success /
    rollback on exception -- same context-manager shape as before."""
    if not settings.is_supabase_configured():
        raise ConfigurationError(
            "SUPABASE_DB_URL is not configured. Set it in your .env file "
            "(see .env.example) or in Streamlit secrets. EcoVision AI "
            "cannot connect to its database without it -- see "
            "supabase/README.md for setup steps."
        )
    try:
        conn = psycopg2.connect(
            settings.SUPABASE_DB_URL,
            cursor_factory=psycopg2.extras.RealDictCursor,
        )
    except psycopg2.OperationalError as e:
        raise ConfigurationError(
            f"Could not connect to the EcoVision AI database. Check that "
            f"SUPABASE_DB_URL is correct and the database is reachable. "
            f"Underlying error: {e}"
        ) from e

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        logger.exception("Database error — transaction rolled back")
        raise
    finally:
        conn.close()


def init_db():
    """Readiness/connectivity check only — see this module's docstring
    for why table creation and seeding moved to supabase/migrations/."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")


def _translate(query: str) -> tuple[str, bool]:
    """Apply the two mechanical, fully-audited translations described in
    this module's docstring. Returns (translated_query, is_insert)."""
    q = query.replace("?", "%s")

    stripped_upper = q.strip().upper()
    if stripped_upper.startswith("INSERT OR IGNORE INTO"):
        # "INSERT OR IGNORE INTO" -> "INSERT INTO ... ON CONFLICT DO NOTHING"
        q = q.strip()
        q = "INSERT INTO" + q[len("INSERT OR IGNORE INTO"):]
        q = q.rstrip().rstrip(";") + " ON CONFLICT DO NOTHING"

    is_insert = q.strip().upper().startswith("INSERT")
    if is_insert and "RETURNING" not in q.upper():
        q = q.rstrip().rstrip(";") + " RETURNING id"

    return q, is_insert


def execute(query: str, params: tuple = ()):
    """INSERT/UPDATE/DELETE. Returns the new row's id for an INSERT
    (matching the previous sqlite3 cur.lastrowid contract every existing
    caller already relies on), or None for UPDATE/DELETE/an
    ON-CONFLICT-skipped INSERT (no existing caller uses the return value
    in either of those cases — verified during the Phase 2A audit)."""
    q, is_insert = _translate(query)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(q, params)
            if is_insert:
                row = cur.fetchone()
                return row["id"] if row else None
            return None


def fetch_one(query: str, params: tuple = ()):
    q, _ = _translate(query)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(q, params)
            row = cur.fetchone()
            return dict(row) if row is not None else None


def fetch_all(query: str, params: tuple = ()):
    q, _ = _translate(query)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(q, params)
            return [dict(r) for r in cur.fetchall()]
