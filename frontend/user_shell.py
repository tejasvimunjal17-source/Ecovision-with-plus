"""
frontend/user_shell.py
--------------------------
PHASE 1 — the authenticated "User Dashboard" sidebar shell for citizens
and officers, rendered in place of Streamlit's own auto-generated
page-nav list (hidden via frontend/custom_sidebar.py's
`[data-testid="stSidebarNav"] { display: none; }` rule).

This file renders ONLY navigation — st.page_link() calls that point at
the exact same, unmodified files in pages/. It does not read or write
any complaint, reward, or user data itself; it does not duplicate or
reimplement any page's business logic. Every link still resolves to a
page that independently calls require_login(allowed_roles=[...]) at
its own top (see utils/helpers.py) — hiding a link here is a UX
convenience, never the security boundary. A citizen who guesses/types
the URL for Officer Dashboard or Admin Dashboard is still blocked by
that page's own require_login() call, completely unchanged.

Why resolve pages by numeric prefix instead of a hardcoded path
--------------------------------------------------------------------
Every file in pages/ is named "<n>_<emoji>_<Title>.py". Hardcoding the
exact emoji byte sequence in this file would be fragile across
different filesystems/zip tools (some environments normalize or
mangle multi-codepoint emoji in filenames on extraction). Since the
leading "<n>_" numeric prefix is the part Streamlit's own page-sorting
already depends on and is guaranteed unique and stable, `_page()`
below resolves each link by globbing for that prefix instead of
spelling out the emoji — this is presentation-layer robustness, not a
routing change: it still resolves to the exact same on-disk file
st.page_link() would otherwise be pointed at literally.

Called from utils.helpers.load_css() only when a NON-admin user is
signed in (st.session_state["user"]["role"] in {"citizen", "officer"}).
Admins get frontend/admin_shell.py instead — see that file and
utils/helpers.py for the exact routing logic.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from components.ui import sidebar_brand, nav_section_label
from utils.helpers import logout

_PAGES_DIR = Path(__file__).resolve().parent.parent / "pages"


def _page(prefix: str) -> str | None:
    """Resolve 'pages/<prefix>_....py' by numeric prefix. Returns the
    st.page_link()-compatible relative path, or None if the file isn't
    found (defensive — link is simply skipped rather than raising, so a
    future rename in pages/ degrades gracefully instead of crashing
    every authenticated page)."""
    matches = sorted(_PAGES_DIR.glob(f"{prefix}_*.py"))
    if not matches:
        return None
    return f"pages/{matches[0].name}"


# Every entry below points at an EXISTING EcoVision page — no new pages
# were created for Phase 1. "roles" is the set of roles this nav item
# is shown to (independent of, and secondary to, each page's own
# require_login() gate).
_NAV_ITEMS = [
    # (prefix, icon, label, roles)
    ("3", "🏠", "Home", {"citizen"}),
    ("7", "🏠", "Home", {"officer"}),
    ("4", "📢", "Report Waste", {"citizen"}),
    ("5", "📜", "Complaint History", {"citizen"}),
    ("6", "🏆", "Rewards", {"citizen"}),
    ("10", "♻️", "Recycling Guide", {"citizen", "officer"}),
    ("11", "🌍", "Carbon Calculator", {"citizen", "officer"}),
    ("13", "📍", "Recycling Centres", {"citizen", "officer"}),
    ("14", "🌱", "Awareness Hub", {"citizen", "officer"}),
    ("15", "🎓", "Certifications & Jobs", {"citizen", "officer"}),
    ("16", "📄", "Reports", {"citizen", "officer"}),
    ("17", "ℹ️", "About / Contact", {"citizen", "officer"}),
]


def render_user_sidebar(user: dict) -> None:
    """Render the User Dashboard sidebar for a signed-in citizen or
    officer. Call once per page load, from utils.helpers.load_css()."""
    role = user.get("role", "citizen")

    with st.sidebar:
        sidebar_brand(
            "🌎 EcoVision AI",
            subtitle=f"Hi, {user.get('full_name', 'there').split()[0]} 👋",
            role_label=role.upper(),
        )
        st.markdown("---")

        nav_section_label("Navigation")
        for prefix, icon, label, roles in _NAV_ITEMS:
            if role not in roles:
                continue
            path = _page(prefix)
            if path:
                st.page_link(path, label=label, icon=icon)

        st.markdown("---")
        nav_section_label("Account")

        # Presentation-only preference for now (stored so a later phase
        # can wire up an actual light-mode stylesheet without another
        # session-state migration) — does not change any page's CSS yet,
        # since assets/style.css only ships a dark theme today.
        current_theme = st.session_state.get("theme", "dark")
        theme_toggle = st.toggle("🌙 Dark Mode", value=(current_theme == "dark"), key="eco_theme_toggle")
        new_theme = "dark" if theme_toggle else "light"
        if new_theme != current_theme:
            st.session_state["theme"] = new_theme

        if st.button("🚪 Logout", key="eco_user_logout", use_container_width=True):
            logout()
            st.rerun()
