-- ============================================================================
-- EcoVision AI — Supabase PostgreSQL migration 002: complaints
-- Depends on: 001_init_schema.sql (users)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 4. complaints — replaces SQLite's complaints table (backend/complaints.py).
--    Every column preserved, including ai_predicted_category / ai_confidence
--    (currently populated by utils/ai_client.py but not yet read back
--    anywhere in the UI — kept as-is per "preserve all existing columns").
-- ----------------------------------------------------------------------------
create table if not exists complaints (
    id                      bigint generated always as identity primary key,
    user_id                 bigint not null references users(id) on delete cascade,
    category                text not null,
    ai_predicted_category   text,
    ai_confidence           double precision,
    description             text,
    ai_description          text,
    priority                text default 'Medium'
                                check (priority in ('Low', 'Medium', 'High')),
    status                  text default 'Submitted',
    image_path              text,
    latitude                double precision,
    longitude               double precision,
    ward                    text,
    address_text            text,
    assigned_officer_id     bigint references users(id),
    assigned_worker         text,
    officer_notes           text,
    created_at              timestamptz not null default now(),
    updated_at              timestamptz not null default now(),
    resolved_at             timestamptz
);

-- ----------------------------------------------------------------------------
-- 5. complaint_timeline — replaces SQLite's complaint_timeline table.
-- ----------------------------------------------------------------------------
create table if not exists complaint_timeline (
    id              bigint generated always as identity primary key,
    complaint_id    bigint not null references complaints(id) on delete cascade,
    status          text not null,
    note            text,
    changed_by      bigint references users(id),
    created_at      timestamptz not null default now()
);
