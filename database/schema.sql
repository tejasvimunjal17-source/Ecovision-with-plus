-- ==============================================================
-- EcoVision AI  |  Smart Waste Management Platform
-- SQLite Database Schema
-- ==============================================================

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name       TEXT NOT NULL,
    email           TEXT NOT NULL UNIQUE,
    phone           TEXT,
    password_hash   TEXT NOT NULL,
    salt            TEXT NOT NULL,
    role            TEXT NOT NULL DEFAULT 'citizen' CHECK (role IN ('citizen','officer','admin')),
    ward            TEXT,
    address         TEXT,
    avatar_path     TEXT,
    security_question TEXT,
    security_answer_hash TEXT,
    reward_points   INTEGER DEFAULT 0,
    is_active       INTEGER DEFAULT 1,
    created_at      TEXT DEFAULT (datetime('now')),
    last_login      TEXT
);

CREATE TABLE IF NOT EXISTS categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    description TEXT,
    icon        TEXT,
    disposal_guide TEXT,
    is_active   INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS complaints (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category            TEXT NOT NULL,
    ai_predicted_category TEXT,
    ai_confidence       REAL,
    description         TEXT,
    ai_description      TEXT,
    priority            TEXT DEFAULT 'Medium' CHECK (priority IN ('Low','Medium','High')),
    status              TEXT DEFAULT 'Submitted',
    image_path          TEXT,
    latitude            REAL,
    longitude           REAL,
    ward                TEXT,
    address_text        TEXT,
    assigned_officer_id INTEGER REFERENCES users(id),
    assigned_worker     TEXT,
    officer_notes       TEXT,
    created_at          TEXT DEFAULT (datetime('now')),
    updated_at          TEXT DEFAULT (datetime('now')),
    resolved_at         TEXT
);

CREATE TABLE IF NOT EXISTS complaint_timeline (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id INTEGER NOT NULL REFERENCES complaints(id) ON DELETE CASCADE,
    status       TEXT NOT NULL,
    note         TEXT,
    changed_by   INTEGER REFERENCES users(id),
    created_at   TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS rewards (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    points     INTEGER NOT NULL,
    reason     TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS chat_history (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER REFERENCES users(id) ON DELETE CASCADE,
    session_id TEXT,
    role       TEXT NOT NULL CHECK (role IN ('user','assistant')),
    message    TEXT NOT NULL,
    language   TEXT DEFAULT 'en',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS recycling_centres (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    type       TEXT,
    address    TEXT,
    ward       TEXT,
    latitude   REAL,
    longitude  REAL,
    contact    TEXT,
    materials_accepted TEXT,
    is_active  INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS carbon_records (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    transport_kg  REAL DEFAULT 0,
    electricity_kg REAL DEFAULT 0,
    plastic_kg    REAL DEFAULT 0,
    water_kg      REAL DEFAULT 0,
    food_kg       REAL DEFAULT 0,
    waste_kg      REAL DEFAULT 0,
    total_score   REAL,
    created_at    TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS login_attempts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    email      TEXT NOT NULL,
    success    INTEGER NOT NULL,
    ip_hint    TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS audit_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER REFERENCES users(id),
    action     TEXT NOT NULL,
    details    TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_complaints_user ON complaints(user_id);
CREATE INDEX IF NOT EXISTS idx_complaints_status ON complaints(status);
CREATE INDEX IF NOT EXISTS idx_complaints_ward ON complaints(ward);
CREATE INDEX IF NOT EXISTS idx_chat_user ON chat_history(user_id);
CREATE INDEX IF NOT EXISTS idx_login_email ON login_attempts(email);
