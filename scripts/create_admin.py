"""
scripts/create_admin.py
---------------------------
Safe replacement for the old database/db.py::_seed_admin() behavior,
which used to silently create a hardcoded admin account
(admin@ecovision.local / Admin@12345) every time init_db() ran against
a fresh SQLite file.

That was reasonable for a local, gitignored, throwaway SQLite file —
it is NOT reasonable for a real cloud Postgres database: a hardcoded
password (even a fake "please change me" one) has no business in a
checked-in supabase/migrations/*.sql file, since that file's contents
end up in git history indefinitely.

WHAT THIS SCRIPT DOES INSTEAD
---------------------------------
Run this ONCE, manually, by whoever is standing up a new EcoVision AI
environment (after applying supabase/migrations/001-006):

    python scripts/create_admin.py

It will:
  1. Confirm SUPABASE_DB_URL is configured (via config.settings).
  2. Check whether an admin account already exists — if so, it exits
     without doing anything (safe to re-run).
  3. Prompt (interactively, via getpass — never as a command-line
     argument, so it never ends up in shell history) for the new
     admin's full name, email, phone, and password.
  4. Hash the password using backend.auth.hash_password() — the EXACT
     same PBKDF2-HMAC-SHA256 + per-user-salt function login_user() and
     verify_password() already use, so the created account logs in
     exactly like any other, with zero special-casing anywhere else in
     the app.
  5. Insert the row via database.db.execute() — the same adapter every
     other part of the app already goes through.

This script is NOT imported or run automatically by app.py or any
page — it is a standalone, opt-in operational tool.
"""
from __future__ import annotations

import getpass
import sys

from database.db import execute, fetch_one, ConfigurationError
from backend.auth import hash_password, validate_password_strength, EMAIL_RE


def main() -> None:
    # PHASE 3D fix: this docstring above has always claimed step 1 is
    # "confirm SUPABASE_DB_URL is configured" -- but the code never
    # actually did that; an unconfigured environment previously hit an
    # uncaught ConfigurationError from fetch_one() below, printing a raw
    # Python traceback instead of a clean message. Wrapping the first
    # database call is enough: get_connection() (called internally by
    # every database.db function) raises ConfigurationError up front on
    # ANY call if SUPABASE_DB_URL is missing/placeholder/unreachable, so
    # catching it once here — matching the exact same
    # try/except ConfigurationError + clear message pattern app.py and
    # utils/helpers.py already use for their own init_db() calls —
    # covers this whole function.
    try:
        existing = fetch_one("SELECT id, email FROM users WHERE role='admin' LIMIT 1")
    except ConfigurationError as e:
        print(f"Can't reach the database: {e}")
        sys.exit(1)

    if existing:
        print(f"An admin account already exists ({existing['email']}). Nothing to do.")
        return

    print("No admin account found. Let's create one.\n")

    full_name = input("Full name: ").strip()
    email = input("Email: ").strip().lower()
    if not EMAIL_RE.match(email):
        print("That doesn't look like a valid email address. Aborting.")
        sys.exit(1)

    phone = input("Phone (optional): ").strip()
    ward = input("Ward (optional, e.g. HQ): ").strip() or "HQ"

    password = getpass.getpass("Password (input hidden): ")
    ok, msg = validate_password_strength(password)
    if not ok:
        print(f"Password rejected: {msg}")
        sys.exit(1)
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("Passwords did not match. Aborting.")
        sys.exit(1)

    pw_hash, salt = hash_password(password)
    execute(
        """INSERT INTO users (full_name, email, phone, password_hash, salt, role, ward)
           VALUES (?,?,?,?,?,?,?)""",
        (full_name, email, phone, pw_hash, salt, "admin", ward),
    )
    print(f"\nAdmin account created: {email}")


if __name__ == "__main__":
    main()
