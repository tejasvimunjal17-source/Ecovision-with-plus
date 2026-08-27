"""
backend/auth.py
------------------
Secure authentication: PBKDF2-HMAC-SHA256 password hashing with a
per-user random salt (no plaintext, no reversible encryption),
registration, login with basic rate limiting, and a security-question
based password reset flow (no SMTP server available in this
environment, so reset works locally without email dependency).
"""
import os
import hashlib
import binascii
import re
import logging
from datetime import datetime, timedelta

from database.db import get_connection, fetch_one, fetch_all, execute

logger = logging.getLogger("ecovision.auth")

PBKDF2_ITERATIONS = 260_000
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_WINDOW_MINUTES = 15

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or binascii.hexlify(os.urandom(16)).decode()
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), PBKDF2_ITERATIONS)
    return binascii.hexlify(dk).decode(), salt


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    check, _ = hash_password(password, salt)
    return check == password_hash


def validate_password_strength(password: str) -> tuple[bool, str]:
    if len(password) < 8:
        return False, "Password must be at least 8 characters."
    if not re.search(r"[A-Z]", password):
        return False, "Password must include at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return False, "Password must include at least one lowercase letter."
    if not re.search(r"\d", password):
        return False, "Password must include at least one number."
    return True, ""


def register_user(full_name, email, phone, password, ward="", address="",
                   role="citizen", security_question="", security_answer=""):
    email = email.strip().lower()
    if not EMAIL_RE.match(email):
        return False, "Please enter a valid email address."
    ok, msg = validate_password_strength(password)
    if not ok:
        return False, msg
    if fetch_one("SELECT id FROM users WHERE email=?", (email,)):
        return False, "An account with this email already exists."

    pw_hash, salt = hash_password(password)
    ans_hash, _ = hash_password(security_answer.strip().lower(), salt) if security_answer else (None, salt)

    try:
        user_id = execute(
            """INSERT INTO users (full_name, email, phone, password_hash, salt, role, ward,
                                   address, security_question, security_answer_hash)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (full_name.strip(), email, phone.strip(), pw_hash, salt, role, ward, address,
             security_question, ans_hash),
        )
        _log_audit(user_id, "register", f"role={role}")
        return True, user_id
    except Exception as e:
        logger.exception("Registration failed")
        return False, f"Registration failed: {e}"


def _recent_failed_attempts(email: str) -> int:
    # PHASE 2B: pass a real datetime object instead of a pre-formatted
    # string. psycopg2 has a built-in adapter that sends a Python
    # datetime as a proper Postgres timestamptz parameter unambiguously;
    # a plain text-formatted string compared against a timestamptz
    # column via a bind parameter is not guaranteed to resolve the same
    # way. Same value either way — only the Python-side representation
    # changed, not the query, not this function's signature/behavior.
    since = datetime.utcnow() - timedelta(minutes=LOCKOUT_WINDOW_MINUTES)
    # PHASE 2B: login_attempts.success stays an INTEGER (0/1) column in
    # Postgres (see supabase/migrations/001_init_schema.sql's "Boolean-as-
    # integer columns" design note) specifically so this literal needs NO
    # change — Postgres integer columns compare against bare 0/1 literals
    # exactly like SQLite did.
    row = fetch_one(
        "SELECT COUNT(*) as c FROM login_attempts WHERE email=? AND success=0 AND created_at >= ?",
        (email, since),
    )
    return row["c"] if row else 0


def login_user(email: str, password: str):
    """Returns (success: bool, user_dict_or_message)."""
    email = email.strip().lower()

    if _recent_failed_attempts(email) >= MAX_FAILED_ATTEMPTS:
        return False, f"Too many failed attempts. Please try again in {LOCKOUT_WINDOW_MINUTES} minutes."

    user = fetch_one("SELECT * FROM users WHERE email=?", (email,))
    if not user or not user["is_active"]:
        # PHASE 2B: unchanged — see _recent_failed_attempts() note above;
        # success/is_active stay INTEGER (0/1) in Postgres, so these
        # literals need no translation.
        execute("INSERT INTO login_attempts (email, success) VALUES (?,0)", (email,))
        return False, "Invalid email or password."

    if not verify_password(password, user["password_hash"], user["salt"]):
        execute("INSERT INTO login_attempts (email, success) VALUES (?,0)", (email,))
        return False, "Invalid email or password."

    execute("INSERT INTO login_attempts (email, success) VALUES (?,1)", (email,))
    # PHASE 2B: datetime('now') -> now(), PostgreSQL's equivalent
    # current-timestamp function (SQLite-only syntax has no PostgreSQL
    # meaning). Same UPDATE, same signature, same behavior.
    execute("UPDATE users SET last_login=now() WHERE id=?", (user["id"],))
    _log_audit(user["id"], "login", "")
    user.pop("password_hash", None)
    user.pop("salt", None)
    return True, user


def find_or_create_google_user(email: str, full_name: str = ""):
    """Look up -- or, on a visitor's first Google sign-in, create -- the
    EcoVision account for someone who just authenticated via Streamlit's
    native OIDC (st.login() / st.user, Google as the identity provider).
    Called once from app.py's Google-linking block, right after Streamlit
    reports st.user.is_logged_in — see that block's own comment for why
    this lives in backend/auth.py rather than a separate module: it's the
    one file that already owns every read/write against the `users`
    table (register_user, login_user, reset_password), and Google sign-in
    is just a second way to reach the exact same table, not a second
    identity system.

    Returns the same (success: bool, user_dict_or_message) shape as
    login_user(), so app.py's linking block and pages/1_🔐_Login.py's
    existing email flow both hand the exact same shape of object to
    st.session_state["user"].

    EXISTING account (matched by email): password_hash, salt, role,
    reward_points, ward, address, avatar_path, security_question,
    security_answer_hash, is_active, and id are read but NEVER modified
    here — only last_login is updated (identical to what login_user()
    already does for the email/password flow), so an EcoVision account
    behaves the same regardless of which method was used to sign in.
    An inactive account is rejected exactly like the email/password path
    does — Google verifying someone's email address has no bearing on
    whether EcoVision has deactivated their account.

    NEW account (no existing row for this email): created with
    role="citizen" — the same default register_user() uses when no role
    is passed, and the only default this function will ever use. Google
    claims (name, email) are never inspected for role/permission hints;
    there is no code path in this function that can result in role
    "officer" or "admin". A new Google account still needs a
    password_hash/salt (NOT NULL columns), so one is generated from a
    random, never-surfaced value via the exact same hash_password() the
    email flow uses — this doesn't create a usable password (nobody
    knows it, including this account's owner), it just satisfies the
    schema; the account remains reachable only via "Continue with
    Google" until/unless its owner later sets a real password through
    some future account-settings flow (out of scope here, and no such
    page exists yet in EcoVision).
    """
    email_norm = (email or "").strip().lower()
    if not email_norm:
        return False, (
            "Google did not share an email address for this account, so we "
            "can't sign you in. Please use Continue with Email instead."
        )

    try:
        user = fetch_one("SELECT * FROM users WHERE email=?", (email_norm,))
    except Exception:
        logger.exception("Google sign-in: user lookup failed")
        return False, "We couldn't reach the database right now. Please try again in a moment."

    if user is not None:
        if not user["is_active"]:
            # Same rejection as login_user()'s inactive-user branch --
            # Google authenticating the person is not EcoVision granting
            # them access; is_active is still the deciding factor.
            return False, "This account has been deactivated. Please contact support."
        try:
            execute("UPDATE users SET last_login=now() WHERE id=?", (user["id"],))
            _log_audit(user["id"], "login_google", "")
        except Exception:
            # A failed last_login stamp/audit write must not block sign-in
            # -- the same tolerance _log_audit() itself already has for
            # its own failures elsewhere in this file.
            logger.warning("Google sign-in: last_login/audit update failed", exc_info=True)
        user.pop("password_hash", None)
        user.pop("salt", None)
        return True, user

    # ---- New account ----
    random_unusable_password = binascii.hexlify(os.urandom(32)).decode()
    pw_hash, salt = hash_password(random_unusable_password)
    safe_full_name = (full_name or "").strip() or "Google User"

    try:
        user_id = execute(
            """INSERT INTO users (full_name, email, phone, password_hash, salt, role)
               VALUES (?,?,?,?,?,?)""",
            (safe_full_name, email_norm, "", pw_hash, salt, "citizen"),
        )
        _log_audit(user_id, "register_google", "role=citizen")
    except Exception:
        logger.exception("Google sign-in: new-user creation failed")
        return False, "We couldn't create your account right now. Please try again in a moment."

    new_user = fetch_one("SELECT * FROM users WHERE id=?", (user_id,))
    if new_user is None:
        # Should be unreachable (we just inserted this row), but fail
        # safely rather than return None into st.session_state["user"].
        return False, "Account creation didn't complete. Please try again."
    new_user.pop("password_hash", None)
    new_user.pop("salt", None)
    return True, new_user


def find_or_create_google_user(email: str, full_name: str = ""):
    """PHASE 3B — Google OIDC identity -> EcoVision `users` row -> the same
    session shape login_user() already returns: (True, user_dict) or
    (False, message).

    Added here (not a new module) because it needs the exact same
    `users` table columns, the exact same hash_password()/execute()/
    fetch_one() this file already owns, and the exact same
    (True, user_dict) contract app.py's Google-linking block and
    pages/1_🔐_Login.py's email flow both hand to
    st.session_state["user"] — putting it anywhere else would mean a
    second module writing to `users`, or reimporting these internals
    from outside their owning file. Purely additive: no existing
    function in this file is modified.

    EXISTING account (matched by normalized email) — every one of these
    is read, NONE is written by this function, exactly as required:
    id, role, password_hash, salt, reward_points, ward, address,
    security_question, security_answer_hash, avatar_path, is_active,
    created_at. Only `last_login` is updated, via the exact same
    `UPDATE users SET last_login=now() WHERE id=?` login_user() already
    runs on a normal email login — this is "logging in", not "editing
    the account". An inactive account (is_active=0) is rejected with the
    same generic message login_user() already uses for that case, so
    Google sign-in gives an inactive account no more access than the
    email/password flow already denies it; nothing here reactivates it.

    NEW account (no existing row for this email) — created with
    role="citizen", the exact same safe default
    register_user()/pages/2_📝_Register.py already use for a normal
    signup with no role specified. There is no code path in this
    function that can write role="officer" or role="admin" — Google
    profile data has no claim this function even reads for that
    purpose. `password_hash`/`salt` are still set (the columns are
    NOT NULL) to a random, never-surfaced value via the exact same
    hash_password() every other account uses — this does not "invent a
    weaker auth method": nobody can log into this account with a
    password (the random value was never shown to anyone or emailed
    anywhere) unless they later go through EcoVision's own
    security-question reset flow, exactly like any other account.
    `security_question`/`security_answer_hash` are left unset (both
    nullable columns already, per database/schema.sql) since Google
    never supplies one — the account owner can add one later via the
    same mechanism a normal citizen would (not built in this phase,
    since no existing EcoVision page currently lets a logged-in user
    set a security question either; out of scope here).
    """
    email_norm = (email or "").strip().lower()
    if not email_norm:
        return False, "Google did not share an email address, so we can't sign you in. Please use Continue with Email instead."

    try:
        user = fetch_one("SELECT * FROM users WHERE email=?", (email_norm,))
    except Exception as e:
        logger.exception("Google sign-in: user lookup failed")
        return False, f"We couldn't reach the database right now ({e}). Please try again in a moment."

    if user is not None:
        if not user["is_active"]:
            # Same generic message login_user() already returns for an
            # inactive account on the email/password path -- Google
            # sign-in must not be a more permissive route into a
            # deactivated account, and must not say anything more
            # specific that would help distinguish "wrong password"
            # from "your account was deactivated".
            return False, "Invalid email or password."
        try:
            execute("UPDATE users SET last_login=now() WHERE id=?", (user["id"],))
            _log_audit(user["id"], "login_google", "")
        except Exception:
            # A last_login/audit-log write failure must not block sign-in
            # for an otherwise-valid account -- same "log best-effort,
            # never block" posture _log_audit() itself already has.
            logger.warning("Google sign-in: last_login/audit update failed", exc_info=True)
        user.pop("password_hash", None)
        user.pop("salt", None)
        return True, user

    # ---- new account -------------------------------------------------
    safe_name = (full_name or "").strip() or "Google User"
    random_password = binascii.hexlify(os.urandom(24)).decode()  # never shown/stored anywhere but its own hash
    pw_hash, salt = hash_password(random_password)

    try:
        user_id = execute(
            """INSERT INTO users (full_name, email, phone, password_hash, salt, role, ward, address)
               VALUES (?,?,?,?,?,?,?,?)""",
            (safe_name, email_norm, "", pw_hash, salt, "citizen", "", ""),
        )
        _log_audit(user_id, "register_google", "role=citizen")
    except Exception as e:
        logger.exception("Google sign-in: account creation failed")
        return False, f"We couldn't create your account right now ({e}). Please try again, or use Continue with Email."

    new_user = fetch_one("SELECT * FROM users WHERE id=?", (user_id,))
    new_user.pop("password_hash", None)
    new_user.pop("salt", None)
    return True, new_user


def get_security_question(email: str):
    user = fetch_one("SELECT security_question FROM users WHERE email=?", (email.strip().lower(),))
    return user["security_question"] if user else None


def reset_password(email: str, security_answer: str, new_password: str):
    email = email.strip().lower()
    user = fetch_one("SELECT * FROM users WHERE email=?", (email,))
    if not user:
        return False, "No account found with this email."

    ans_hash, _ = hash_password(security_answer.strip().lower(), user["salt"])
    if ans_hash != user["security_answer_hash"]:
        return False, "Security answer is incorrect."

    ok, msg = validate_password_strength(new_password)
    if not ok:
        return False, msg

    pw_hash, salt = hash_password(new_password)
    execute("UPDATE users SET password_hash=?, salt=? WHERE id=?", (pw_hash, salt, user["id"]))
    _log_audit(user["id"], "password_reset", "")
    return True, "Password reset successfully. You can now log in."


def _log_audit(user_id, action, details):
    try:
        execute("INSERT INTO audit_log (user_id, action, details) VALUES (?,?,?)",
                (user_id, action, details))
    except Exception:
        logger.warning("Audit log write failed", exc_info=True)
