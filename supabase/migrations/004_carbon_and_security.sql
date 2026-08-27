-- ============================================================================
-- EcoVision AI — Supabase PostgreSQL migration 004: carbon tracking + security
-- Depends on: 001_init_schema.sql (users)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 8. carbon_records — replaces SQLite's carbon_records table
--    (pages/11_Carbon_Calculator.py — currently write-only in the app;
--    kept as a real table since it's genuine user data already being
--    collected, per Phase 2A's "preserve all existing tables" finding).
-- ----------------------------------------------------------------------------
create table if not exists carbon_records (
    id              bigint generated always as identity primary key,
    user_id         bigint not null references users(id) on delete cascade,
    transport_kg    double precision default 0,
    electricity_kg  double precision default 0,
    plastic_kg      double precision default 0,
    water_kg        double precision default 0,
    food_kg         double precision default 0,
    waste_kg        double precision default 0,
    total_score     double precision,
    created_at      timestamptz not null default now()
);

-- ----------------------------------------------------------------------------
-- 9. login_attempts — replaces SQLite's login_attempts table
--    (backend/auth.py rate-limiting). `success` intentionally stays
--    INTEGER (0/1), not boolean — see 001_init_schema.sql's header
--    comment and supabase/README.md.
-- ----------------------------------------------------------------------------
create table if not exists login_attempts (
    id          bigint generated always as identity primary key,
    email       text not null,
    success     integer not null,
    ip_hint     text,
    created_at  timestamptz not null default now()
);

-- ----------------------------------------------------------------------------
-- 10. audit_log — replaces SQLite's audit_log table (backend/auth.py
--     _log_audit() — register / login / password_reset events).
-- ----------------------------------------------------------------------------
create table if not exists audit_log (
    id          bigint generated always as identity primary key,
    user_id     bigint references users(id),
    action      text not null,
    details     text,
    created_at  timestamptz not null default now()
);
