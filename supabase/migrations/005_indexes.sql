-- ============================================================================
-- EcoVision AI — Supabase PostgreSQL migration 005: indexes
-- Depends on: 001-004 (all tables must exist first)
-- ============================================================================

-- Exact translations of the 5 indexes already defined in the original
-- database/schema.sql:
create index if not exists idx_complaints_user   on complaints(user_id);
create index if not exists idx_complaints_status on complaints(status);
create index if not exists idx_complaints_ward   on complaints(ward);
create index if not exists idx_chat_user         on chat_history(user_id);
create index if not exists idx_login_email       on login_attempts(email);

-- One NEW index, not present in the original schema.sql: every existing
-- lookup of a user by email in backend/auth.py (register_user,
-- login_user, get_security_question, reset_password) always lowercases
-- the email first (email.strip().lower()) before the WHERE email=?
-- comparison. SQLite's default b-tree index on `email` already served
-- these lookups adequately at SQLite's scale; adding a matching
-- functional index here is a pure performance improvement with zero
-- behavior change — every query is still comparing lowercased
-- application-supplied values against this expression index.
create index if not exists idx_users_email_lower on users(lower(email));
