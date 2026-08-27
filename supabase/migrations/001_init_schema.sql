-- ============================================================================
-- EcoVision AI — Supabase PostgreSQL migration 001: core reference tables
-- Run in order (001 -> 007) via the Supabase SQL Editor or `supabase db push`.
-- Idempotent: safe to re-run (uses IF NOT EXISTS everywhere).
--
-- PRIMARY KEY DESIGN DECISION (Phase 2B):
-- EcoVision's existing integer AUTOINCREMENT ids are PRESERVED, using
-- Postgres's `bigint generated always as identity` — the modern
-- (Postgres 10+) equivalent of SQLite's `INTEGER PRIMARY KEY
-- AUTOINCREMENT`. UUIDs (LearnMate's convention) were deliberately NOT
-- adopted: there is no concrete technical reason PostgreSQL/Supabase
-- can't preserve integer ids, and doing so avoids real application-code
-- changes that UUIDs would force — e.g. pages/8_Admin_Dashboard.py's
-- `st.number_input("User ID to toggle active status", ...)` widget
-- assumes an integer id today. Keeping integer ids means that widget,
-- and every other id comparison/display in the existing app, needs
-- ZERO changes. See supabase/README.md "Primary key decision" section
-- for the full reasoning.
--
-- is_active / success columns intentionally stay INTEGER (0/1), not
-- native `boolean` — see supabase/README.md "Boolean-as-integer
-- columns" for why this specific, deliberate choice preserves existing
-- application code (pages/8_Admin_Dashboard.py does
-- `0 if u["is_active"] else 1`; several fetch queries filter
-- `WHERE is_active=1`) without any caller-side changes.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. users — replaces SQLite's users table (backend/auth.py).
--    Same columns, same CHECK constraint on role, same defaults.
-- ----------------------------------------------------------------------------
create table if not exists users (
    id                      bigint generated always as identity primary key,
    full_name               text not null,
    email                   text not null unique,
    phone                   text,
    password_hash           text not null,
    salt                    text not null,
    role                    text not null default 'citizen'
                                check (role in ('citizen', 'officer', 'admin')),
    ward                    text,
    address                 text,
    avatar_path             text,
    security_question       text,
    security_answer_hash    text,
    reward_points           integer default 0,
    is_active               integer default 1,
    created_at              timestamptz not null default now(),
    last_login              timestamptz
);

-- ----------------------------------------------------------------------------
-- 2. categories — replaces SQLite's categories table.
--    UNIQUE(name) preserved — required for the existing
--    "INSERT OR IGNORE ... VALUES (name, ...)" pattern used both by the
--    original seeding logic and by pages/8_Admin_Dashboard.py's
--    "Add Category" form, which database/db.py's execute() now
--    translates to Postgres's "ON CONFLICT DO NOTHING" (see
--    database/db.py's docstring for exactly how).
-- ----------------------------------------------------------------------------
create table if not exists categories (
    id              bigint generated always as identity primary key,
    name            text not null unique,
    description     text,
    icon            text,
    disposal_guide  text,
    is_active       integer default 1
);

-- ----------------------------------------------------------------------------
-- 3. recycling_centres — replaces SQLite's recycling_centres table.
--    No UNIQUE constraint on name in the original schema either — the
--    original seed logic guards on "table is empty", not per-row
--    dedup; see supabase/migrations/007_seed_reference_data.sql for the
--    faithful Postgres translation of that exact guard.
-- ----------------------------------------------------------------------------
create table if not exists recycling_centres (
    id                  bigint generated always as identity primary key,
    name                text not null,
    type                text,
    address             text,
    ward                text,
    latitude            double precision,
    longitude           double precision,
    contact             text,
    materials_accepted  text,
    is_active           integer default 1
);
