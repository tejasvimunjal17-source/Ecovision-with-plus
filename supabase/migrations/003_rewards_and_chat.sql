-- ============================================================================
-- EcoVision AI — Supabase PostgreSQL migration 003: rewards + Prakriti chat
-- Depends on: 001_init_schema.sql (users)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 6. rewards — replaces SQLite's rewards table (backend/complaints.py
--    award_points() / get_user_rewards() / get_leaderboard()).
-- ----------------------------------------------------------------------------
create table if not exists rewards (
    id          bigint generated always as identity primary key,
    user_id     bigint not null references users(id) on delete cascade,
    points      integer not null,
    reason      text,
    created_at  timestamptz not null default now()
);

-- ----------------------------------------------------------------------------
-- 7. chat_history — replaces SQLite's chat_history table
--    (chatbot/prakriti.py save_message() / load_history() / clear_history() —
--    UNCHANGED in Phase 2B; only this table's storage engine changes).
-- ----------------------------------------------------------------------------
create table if not exists chat_history (
    id          bigint generated always as identity primary key,
    user_id     bigint references users(id) on delete cascade,
    session_id  text,
    role        text not null check (role in ('user', 'assistant')),
    message     text not null,
    language    text default 'en',
    created_at  timestamptz not null default now()
);
