# EcoVision AI — Supabase (PostgreSQL) migration

Phase 2B replaced EcoVision AI's local SQLite database with a hosted
Supabase PostgreSQL database, while preserving 100% of the existing
application behavior: authentication, complaints, rewards, analytics,
Prakriti AI chat history, recycling data, and carbon tracking all work
exactly as before — only the storage engine underneath changed.

## Setup (one-time, per environment)

1. Create a Supabase project (or use an existing one).
2. Open **Project Settings → Database → Connection string → URI** and
   copy the connection string. Put it in your `.env` as `SUPABASE_DB_URL`
   (see `.env.example`).
3. In the Supabase **SQL Editor**, run the 6 schema migrations in order:
   `001_init_schema.sql`, `002_complaints.sql`, `003_rewards_and_chat.sql`,
   `004_carbon_and_security.sql`, `005_indexes.sql`, `006_rls.sql`.
4. Run `007_seed_reference_data.sql` to load the 9 waste categories and
   4 recycling centres (identical to the old SQLite seed data).
5. Create your first admin account: `python scripts/create_admin.py`
   (interactive — see that script's own docstring for why this replaces
   the old hardcoded-admin-on-first-run behavior).
6. Run the app as usual (`streamlit run app.py`) — `database/db.py` will
   connect using `SUPABASE_DB_URL` on the first query.

All 7 files are idempotent (`if not exists` / `on conflict do nothing`
throughout) — safe to re-run if you're unsure whether a step already ran.

## Architecture: why a direct Postgres connection, not the REST SDK

Every existing caller in this codebase (`backend/auth.py`,
`backend/complaints.py`, `backend/analytics.py`, `chatbot/prakriti.py`,
and several `pages/*.py` files) talks to the database through exactly
four functions in `database/db.py`: `get_connection()`, `execute()`,
`fetch_one()`, `fetch_all()` — passing hand-written, parameterized raw
SQL strings (joins, `GROUP BY` aggregates, `CASE` expressions, etc).

Supabase's REST API (what the `supabase-py` SDK talks to, authenticated
with `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY`) has no "run this raw
SQL" endpoint — only a fluent table/filter builder
(`.table("x").select("y").eq("z", 1)`), which cannot represent this
codebase's existing queries without rewriting every single one, in every
caller file. That would violate the "keep existing function names and
caller-facing behavior" requirement this migration was built around.

Instead, `database/db.py` connects directly to Postgres via `psycopg2`,
using `SUPABASE_DB_URL` (Supabase exposes this alongside the REST API —
it's the same database, just a different access path). This lets almost
every existing raw SQL string keep running completely unchanged.
`SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` are still captured in
`config/settings.py` for a **future** feature that might genuinely need
the REST API/SDK (e.g. Supabase Storage for complaint photos) — neither
is used by `database/db.py` today.

## Primary key decision: integer, not UUID

EcoVision's existing `INTEGER PRIMARY KEY AUTOINCREMENT` ids were
**preserved**, using PostgreSQL's `bigint generated always as identity`
(the modern, Postgres-10+ equivalent). LearnMate AI's own Supabase
migration uses UUIDs, but that convention was **not** copied here: there
is no concrete technical reason PostgreSQL can't keep integer ids, and
switching to UUIDs would force real application-code changes — most
directly, `pages/8_🛠️_Admin_Dashboard.py`'s
`st.number_input("User ID to toggle active status", ...)` widget assumes
an integer id. Keeping integer ids means that widget, and every other id
comparison/display already in the app, needed zero changes.

## Boolean-as-integer columns: also preserved, on purpose

`users.is_active`, `categories.is_active`, `recycling_centres.is_active`,
and `login_attempts.success` all stay `integer` (storing `0`/`1`) rather
than becoming native PostgreSQL `boolean` columns. This was a deliberate
choice for the same reason as the primary-key decision: several existing
call sites compare/assign these as bare integer literals —
`WHERE is_active=1` (`backend/complaints.py`, `pages/10`, `pages/13`),
`VALUES (?,0)` / `VALUES (?,1)` (`backend/auth.py`'s login-attempt
logging), and `0 if u["is_active"] else 1`
(`pages/8_🛠️_Admin_Dashboard.py`'s active/inactive toggle). PostgreSQL
`integer` columns accept these exact literals with no translation at
all; a native `boolean` column would have required editing all five of
those call sites to use `true`/`false`/Python `bool` instead — a real
behavior-equivalent change, but an unnecessary one given the "preserve
existing application code wherever possible" priority this phase was
built around.

## What `database/db.py` translates automatically (so callers don't have to)

1. **Placeholder syntax**: SQLite's `?` → psycopg2's `%s`, via a plain
   `query.replace("?", "%s")`. Verified safe for this specific, fully
   read codebase — no existing query string contains a literal `?`
   inside a quoted value.
2. **`INSERT OR IGNORE INTO`** → `INSERT INTO ... ON CONFLICT DO
   NOTHING`. Used by exactly one live caller:
   `pages/8_🛠️_Admin_Dashboard.py`'s "Add Category" form (and,
   previously, `database/db.py`'s own seeding functions — now retired,
   see below).
3. **Auto-appended `RETURNING id`** on any `INSERT` that doesn't already
   have one, so `execute()`'s return value keeps meaning "the new row's
   id" — matching `sqlite3`'s `cur.lastrowid`, which PostgreSQL has no
   direct equivalent for. Every table names its primary key `id`, so
   this is safe across the whole schema.

## SQLite → PostgreSQL translations that could NOT be done generically

A handful of vendor-specific SQL *functions* have no safe
string-substitution equivalent — translating them required editing the
specific query, not a mechanical rule in `database/db.py`. Every one of
these preserves its function's existing name, signature, and return
shape — only the SQL text inside changed:

| File | Old (SQLite) | New (PostgreSQL) | Why |
|---|---|---|---|
| `backend/auth.py::login_user()` | `datetime('now')` | `now()` | current-timestamp function |
| `backend/complaints.py::update_status()` (×2) | `datetime('now')` | `now()` | same |
| `backend/complaints.py::assign_officer()` | `datetime('now')` | `now()` | same |
| `backend/analytics.py::kpi_summary()` | `(julianday(resolved_at) - julianday(created_at)) * 24` | `EXTRACT(EPOCH FROM (resolved_at - created_at)) / 3600` | hours-between-two-timestamps has no `julianday()` equivalent; `EXTRACT(EPOCH ...)` returns seconds, so `/3600` replaces `*24` |
| `backend/analytics.py::complaints_daily_trend()` | `date(created_at)` | `created_at::date` | date-part extraction |
| `backend/analytics.py::complaints_daily_trend()` | `datetime('now', '-{days} days')` | `now() - interval '{days} days'` | relative-date arithmetic |
| `backend/analytics.py::complaints_monthly_trend()` | `strftime('%Y-%m', created_at)` | `to_char(created_at, 'YYYY-MM')` | date formatting |

No other file needed changes for date/time or boolean-literal reasons —
confirmed by a full static sweep of `backend/`, `chatbot/`, `pages/`,
`utils/`, `frontend/`, and `components/` for `datetime('now')`,
`julianday`, `strftime(`, and `INSERT OR IGNORE` after the fixes above.

## Row Level Security

EcoVision AI is, and remains, a pure server-side Streamlit application —
`database/db.py` connects with a privileged, backend-only
`SUPABASE_DB_URL`; the browser never talks to Supabase directly. A
privileged Postgres connection bypasses Row Level Security entirely by
Postgres design, so `006_rls.sql` enables RLS on all 10 tables with
**zero permissive policies** — this has no effect on EcoVision's own
queries (they keep working exactly as before). It's pure defense in
depth: if the Supabase anon/public key were ever added to this project
in the future (e.g. for a browser-side feature), it would get zero
access to every table by default.

**The real, functioning access-control boundary remains entirely in
Python**, unchanged by this migration:
- `backend/auth.py` — password hashing, rate limiting
- `utils/helpers.py::require_login(allowed_roles=[...])` — every
  protected page's actual gate
- `backend/complaints.py` — which complaints a citizen/officer/admin can
  see or modify

## Admin account seeding

The old `database/db.py::_seed_admin()` silently created a hardcoded
admin account (`admin@ecovision.local` / `Admin@12345`) on every fresh
SQLite file. That's fine for a local, gitignored, throwaway file — it is
**not** fine for a real cloud database, since a checked-in
`supabase/migrations/*.sql` file's contents live in git history
indefinitely. `007_seed_reference_data.sql` deliberately does **not**
create an admin account. Instead, run `python scripts/create_admin.py`
once per environment — an interactive script that prompts for
credentials via `getpass` (never a command-line argument), hashes the
password with the exact same `backend.auth.hash_password()` every other
account uses, and inserts it through the same `database.db.execute()`
adapter as the rest of the app. See that script's own docstring for
details.

## What `init_db()` does now

Table creation and reference-data seeding no longer happen inside the
running Streamlit app — they live entirely in the 7 migration files
above, applied once via the Supabase SQL Editor or CLI.
`database/db.py::init_db()` is now a lightweight connectivity check
only: it confirms `SUPABASE_DB_URL` is configured and that a connection
can actually be opened, raising a `ConfigurationError` immediately —
caught and shown via `st.error()` + `st.stop()` at both existing call
sites (`app.py` and `utils/helpers.py::init_session_state()`), so a
misconfigured environment fails with a clear message instead of a
confusing error partway through a page.

## `database/schema.sql`

Kept as-is, unmodified, as historical/reference material — it documents
the exact SQLite schema this migration was derived from. It is no longer
read by any running code (`database/db.py::init_db()` no longer calls
`executescript()` against it).

## Google OIDC configuration (Phase 3B)

`app.py`'s "Continue with Google" button uses **Streamlit's own native
OIDC support** (`st.login()` / `st.user` / `st.logout()`, Streamlit
≥1.42) — not a custom OAuth implementation, and not a third-party
auth library. There is no separate Google client/SDK dependency to
install; this is all built into the `streamlit` package already in
`requirements.txt`.

### 1. Create a Google OAuth client

In [Google Cloud Console](https://console.cloud.google.com/):

1. Create (or select) a project, then go to **APIs & Services →
   Credentials → Create Credentials → OAuth client ID**.
2. Application type: **Web application**.
3. Under **Authorized redirect URIs**, add your app's URL with the
   path `/oauth2callback` appended — for local development:
   `http://localhost:8501/oauth2callback`. For a real deployment, use
   `https://YOUR-STREAMLIT-DOMAIN/oauth2callback` (substitute your
   actual deployed domain — this repo doesn't know or assume what that
   will be).
4. Copy the resulting **Client ID** and **Client secret**.

### 2. Configure `.streamlit/secrets.toml`

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`
(gitignored — never commit the real file) and fill in:

- `redirect_uri` — the exact same URL you registered in step 1.3.
- `cookie_secret` — any strong random string you generate yourself.
- `client_id` / `client_secret` — from step 1.4.
- `server_metadata_url` — leave as the Google-fixed value already in
  the template (`https://accounts.google.com/.well-known/openid-configuration`).

On a hosting platform without file-based secrets (Streamlit Community
Cloud has its own "Secrets" UI that accepts this exact same TOML
format — paste the same `[auth]` block there instead of committing a
file).

### 3. What happens if this isn't configured

Nothing breaks. `app.py`'s `google_signed_in()` check (in
`utils/helpers.py`) and the "Continue with Google" button's own
try/except both fail closed and safe: the button shows a plain
"Google Sign-In isn't configured on this deployment... use Continue
with Email" message. Every other part of the app — email/password
registration, login, the User Dashboard, the Admin Panel — is
completely unaffected.

### 4. How "Continue with Google" works end to end

```
"Continue with Google" button (app.py)
        ↓
st.login()  — Streamlit redirects to Google's consent screen
        ↓
Google redirects back to /oauth2callback (handled internally by
Streamlit — you never see or write this route yourself)
        ↓
st.user.is_logged_in becomes True
        ↓
app.py's "Google OIDC account linking" block (runs at the top of
every rerun, but only ACTS the first time st.session_state["user"]
isn't already set) calls backend.auth.find_or_create_google_user()
        ↓
Existing EcoVision account (matched by email)?
   → logged in AS THAT ACCOUNT — role, password data, reward points,
     ward/address, security question all completely untouched
   → an inactive (is_active=0) account is rejected, same as the
     email/password flow
New email?
   → a new `users` row is created with role="citizen" (the same safe
     default the existing Register page uses) — Google sign-in can
     NEVER create an officer or admin account
        ↓
st.session_state["user"] is set — the exact same session key every
existing page's require_login() already reads — and the visitor is
routed to their dashboard via st.switch_page(), same as the existing
email/password login flow
```

### 5. How "Continue with Email" works (unchanged)

Exactly as before Phase 3B: `st.switch_page("pages/2_📝_Register.py")`,
then the existing, completely untouched `backend/auth.py`
register_user()/login_user() flow.

### 6. Logout

`utils/helpers.py::logout()` clears EcoVision's own session
(`st.session_state["user"]`, `chat_history`) for both login methods,
and additionally calls Streamlit's own `st.logout()` when the current
session is a Google one — otherwise `st.user.is_logged_in` would still
report `True` on the next rerun and the account-linking block above
would silently sign the visitor right back in.

