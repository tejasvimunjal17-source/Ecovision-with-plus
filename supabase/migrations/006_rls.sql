-- ============================================================================
-- EcoVision AI — Supabase PostgreSQL migration 006: Row Level Security
-- Depends on: 001-004 (all tables must exist first)
--
-- ARCHITECTURE (matches Phase 2A's audited recommendation):
-- EcoVision AI is, and remains, a pure server-side Streamlit application.
-- database/db.py connects directly to Postgres using SUPABASE_DB_URL — a
-- privileged, backend-only connection string (see supabase/README.md).
-- The browser never talks to Supabase directly; there is no client-side
-- Supabase JS SDK anywhere in this codebase.
--
-- A privileged Postgres connection (owner/service role) BYPASSES row
-- level security entirely, by Postgres design — RLS only restricts
-- roles that do NOT have BYPASSRLS. This means enabling RLS here, with
-- ZERO permissive policies, has no effect at all on EcoVision's own
-- queries (they keep working exactly as before) — it is purely defense
-- in depth: if the Supabase anon/public key were ever added to this
-- project in the future (e.g. for a browser-side feature), it would get
-- ZERO access to every table by default, rather than silently
-- inheriting whatever Postgres's default (no-RLS) behavior would be.
--
-- Existing application-level authorization is UNCHANGED and remains the
-- real, functioning security boundary:
--   - backend/auth.py: password hashing, rate limiting, session user
--   - utils/helpers.py::require_login(allowed_roles=[...]): every
--     protected page's actual access-control gate
--   - backend/complaints.py: which complaints a citizen/officer/admin
--     can see or modify, enforced in Python, not in Postgres policies
--
-- No policies are created in this migration — see Phase 2A §6 and
-- supabase/README.md "Row Level Security" for the full reasoning.
-- ============================================================================

alter table users               enable row level security;
alter table categories          enable row level security;
alter table recycling_centres   enable row level security;
alter table complaints          enable row level security;
alter table complaint_timeline  enable row level security;
alter table rewards             enable row level security;
alter table chat_history        enable row level security;
alter table carbon_records      enable row level security;
alter table login_attempts      enable row level security;
alter table audit_log           enable row level security;
