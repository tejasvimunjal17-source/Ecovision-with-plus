"""utils/helpers.py — shared UI/session helpers used across pages."""
import streamlit as st
from pathlib import Path
from datetime import datetime

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"


def load_css():
    css_path = ASSETS_DIR / "style.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)

    # PHASE 1 — additive LearnMate-inspired design-token layer (new
    # classes only: sidebar nav-link/active-pill, shell brand header,
    # floating chatbot widget). Loaded IN ADDITION to assets/style.css
    # above, never instead of it — every existing eco-hero/eco-card/
    # eco-pill/eco-stat/eco-footer/chat-bubble-* class keeps working
    # unchanged. See frontend/styles.py's own docstring.
    from frontend.styles import inject_shell_css
    inject_shell_css()

    # ------------------------------------------------------------------
    # PHASE 1 — role-based shell routing (presentation only)
    # ------------------------------------------------------------------
    # Renders ONE of two completely separate sidebar shells depending on
    # the signed-in user's existing `role` column (unchanged: citizen /
    # officer / admin — see database/schema.sql, backend/auth.py):
    #
    #   role == "admin"        -> frontend/admin_shell.py (own drawer,
    #                              own branding, own nav, no chatbot)
    #   role in {citizen,       -> frontend/user_shell.py (own drawer,
    #            officer}          own branding, role-filtered nav)
    #                              + frontend/chatbot_widget.py (floating
    #                              Prakriti AI launcher)
    #   not signed in           -> neither shell renders; only the
    #                              regular (emerald) drawer toggle is
    #                              shown, matching the previous behavior
    #                              for the public landing/Login/Register
    #                              pages.
    #
    # This is a PRESENTATION-ONLY branch: it decides which sidebar
    # WIDGETS render, never which pages are reachable. Every page's own
    # require_login(allowed_roles=[...]) call (unchanged, still the real
    # security boundary) continues to gate direct/typed-URL access
    # completely independently of what's shown here — see each shell
    # file's own docstring for the same caveat.
    user = st.session_state.get("user")
    if user and user.get("role") == "admin":
        from frontend.custom_sidebar import render_admin_sidebar_controls
        from frontend.admin_shell import render_admin_sidebar
        render_admin_sidebar_controls()
        render_admin_sidebar(user)
    else:
        from frontend.custom_sidebar import render_custom_sidebar_controls
        render_custom_sidebar_controls()
        if user:
            from frontend.user_shell import render_user_sidebar
            render_user_sidebar(user)
            from frontend.chatbot_widget import render_prakriti_widget
            render_prakriti_widget(user)


def init_session_state():
    # --- DB safety net ---------------------------------------------------
    # Streamlit multipage apps only execute app.py's top-level code when the
    # user lands on the Home page. If someone opens /Register or any other
    # page directly (a fresh tab, a bookmark, a shared link, Streamlit
    # Cloud's cold start, etc.), app.py's init_db() call never runs. Every
    # page calls init_session_state() (directly or via require_login()),
    # so re-running the same connectivity check here — guarded by a
    # session-state flag so it only runs once per session — guarantees a
    # clear, early error no matter which page is opened first.
    #
    # PHASE 2B: init_db() no longer creates a local SQLite schema (that
    # entire failure mode is gone — see database/db.py's docstring); it's
    # now a Supabase connectivity check that can raise ConfigurationError,
    # so this call needs the same try/except + st.error()/st.stop() guard
    # as app.py's own init_db() call, for the same "clear configuration
    # error, not an obscure database error" reason.
    if not st.session_state.get("_db_initialized"):
        from database.db import init_db, ConfigurationError
        try:
            init_db()
        except ConfigurationError as e:
            st.error(f"⚠️ EcoVision AI can't reach its database.\n\n{e}")
            st.stop()
        st.session_state["_db_initialized"] = True

    defaults = {
        "user": None,
        "theme": "dark",
        "chat_history": [],
        "chat_session_id": datetime.utcnow().strftime("%Y%m%d%H%M%S"),
        "show_chat": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def require_login(allowed_roles=None):
    """Call at the top of a protected page. Stops rendering if unauthorized."""
    init_session_state()
    if not st.session_state.get("user"):
        st.warning("🔒 Please log in to access this page.")
        st.page_link("pages/1_🔐_Login.py", label="Go to Login", icon="🔐")
        st.stop()
    if allowed_roles and st.session_state["user"]["role"] not in allowed_roles:
        st.error("⛔ You don't have permission to view this page.")
        st.stop()


def google_signed_in() -> bool:
    """PHASE 3B — True iff Streamlit's own native-OIDC session (st.user;
    Streamlit >=1.42's st.login()/st.logout()) currently has a signed-in
    identity attached to this browser session. Guarded with getattr
    rather than a bare `st.user` access because `st.user` raises
    AttributeError on a deployment with no `[auth]` block in
    .streamlit/secrets.toml at all — in that case Google sign-in simply
    isn't offered/linked and this returns False; "Continue with Email"
    and everything else in the app is unaffected either way. Mirrors
    LearnMate AI's own `_google_logged_in()` helper (app.py) — shared
    here (not duplicated) since both app.py's Google-linking block AND
    logout() below need the exact same check.
    """
    user = getattr(st, "user", None)
    return bool(user is not None and getattr(user, "is_logged_in", False))


def logout():
    # PHASE 3B: capture BEFORE clearing st.session_state["user"] — this
    # is checking Streamlit's own separate `st.user` OIDC session, not
    # anything being cleared below, but read order doesn't matter here;
    # kept first for readability (mirrors the order LearnMate's app.py
    # sidebar logout button reads it in).
    was_google = google_signed_in()

    st.session_state["user"] = None
    st.session_state["chat_history"] = []

    if was_google:
        # Also end Streamlit's own Google OIDC session (clears its
        # identity cookie). Without this, st.user would still report
        # is_logged_in=True on the very next rerun, and app.py's Google
        # account-linking block would immediately sign this visitor
        # back in — logout() would silently no-op for Google users.
        # st.logout() triggers its own redirect and never returns on
        # success (same control-flow shape as st.switch_page), so every
        # existing call site of logout() — app.py's nav, frontend/
        # user_shell.py, frontend/admin_shell.py, all three unchanged —
        # whose own st.rerun() immediately follows this call, only
        # actually reaches that st.rerun() on the plain email/password
        # logout path. This exact ordering/reasoning mirrors LearnMate
        # AI's own sidebar logout button (app.py).
        st.logout()


def status_badge(status: str) -> str:
    colors = {
        "Submitted": "#64748b", "Under Review": "#f59e0b", "Assigned": "#3b82f6",
        "In Progress": "#8b5cf6", "Resolved": "#10b981", "Rejected": "#ef4444",
    }
    color = colors.get(status, "#64748b")
    return f'<span style="background:{color}22;color:{color};padding:4px 12px;border-radius:20px;font-weight:600;font-size:0.85em;border:1px solid {color}55;">{status}</span>'


def priority_badge(priority: str) -> str:
    colors = {"Low": "#10b981", "Medium": "#f59e0b", "High": "#ef4444"}
    color = colors.get(priority, "#64748b")
    return f'<span style="background:{color}22;color:{color};padding:4px 12px;border-radius:20px;font-weight:600;font-size:0.85em;border:1px solid {color}55;">{priority}</span>'


def toast(message: str, icon: str = "✅"):
    st.toast(message, icon=icon)


def format_datetime(dt_str):
    if not dt_str:
        return "-"
    try:
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%d %b %Y, %I:%M %p")
    except Exception:
        return dt_str
