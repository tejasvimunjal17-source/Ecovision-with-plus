"""
frontend/admin_shell.py
---------------------------
PHASE 1 — the separate Admin Panel sidebar shell, rendered instead of
frontend/user_shell.py whenever the signed-in user's role is "admin"
(see utils.helpers.load_css() for the exact routing logic). This is
what gives EcoVision the same "Admin Panel is a completely separate
presentation context from the User Dashboard" separation LearnMate AI
has — a citizen or officer never sees this shell (role != "admin"),
and this shell never renders the citizen/officer nav items.

IMPORTANT — scope of this file in Phase 1
----------------------------------------------
pages/8_🛠️_Admin_Dashboard.py currently implements ALL admin
functionality (Users, Officers, Complaints, Categories, Analytics,
Settings) as st.tabs() inside ONE page/file, with its own
require_login(allowed_roles=["admin"]) gate and every existing
fetch_all()/execute()/analytics.* call untouched. Per this phase's
explicit scope ("do NOT rewrite Admin Dashboard business logic", "do
NOT modify all 17 pages", "we will migrate pages incrementally after
the foundation is approved"), this file does NOT split that page's
six tabs into six separate routes/files yet — doing so would mean
editing pages/8's internals, which is out of scope for Phase 1.

So for now, the Admin Panel sidebar below exposes ONE working nav
entry — "📊 Admin Dashboard" — that opens the existing, fully-intact
tabbed page exactly as it already works today. The six-section sidebar
shown in the Phase 1 spec (Dashboard / Users / Complaints / Categories
/ Analytics / Settings as separate links) is the intended END STATE
once pages/8's tab bodies are refactored into separately-callable
render functions in a later phase — flagged explicitly in the
Phase 1 report as a follow-up decision point, not silently done here.

Nothing in this file touches backend/, database/, or the Admin
Dashboard page's own logic — this is presentation/navigation only.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from components.ui import sidebar_brand, nav_section_label
from utils.helpers import logout

_PAGES_DIR = Path(__file__).resolve().parent.parent / "pages"


def _page(prefix: str) -> str | None:
    """Same numeric-prefix resolution as frontend/user_shell.py — see
    that file's docstring for why this is preferred over a hardcoded
    emoji filename."""
    matches = sorted(_PAGES_DIR.glob(f"{prefix}_*.py"))
    if not matches:
        return None
    return f"pages/{matches[0].name}"


def render_admin_sidebar(admin_user: dict) -> None:
    """Render the Admin Panel sidebar. Call once per page load, from
    utils.helpers.load_css(), only when the signed-in user's role is
    "admin"."""
    with st.sidebar:
        # .eco-admin-nav scopes the cyan active-nav-pill CSS in
        # frontend/styles.py so it never bleeds into the regular
        # (emerald) user sidebar rendered by frontend/user_shell.py.
        st.markdown('<div class="eco-admin-nav">', unsafe_allow_html=True)

        sidebar_brand(
            "🛡️ EcoVision Admin",
            subtitle=admin_user.get("full_name", "Administrator"),
        )
        st.markdown("---")

        nav_section_label("Admin Panel")
        admin_dashboard_path = _page("8")
        if admin_dashboard_path:
            st.page_link(admin_dashboard_path, label="Admin Dashboard", icon="📊")
        st.caption(
            "Users, Complaints, Categories, Analytics and Settings are "
            "available as tabs inside Admin Dashboard today — see this "
            "file's docstring for the planned follow-up to surface them "
            "as separate sidebar sections."
        )

        st.markdown("---")
        nav_section_label("Account")

        # app.py (the public landing page) is always a safe, valid
        # "back to site" target regardless of role, since admin is not
        # itself in the citizen/officer require_login() allow-lists for
        # pages 3-6 (see this file's module docstring).
        st.page_link("app.py", label="Back to Site", icon="↩️")

        if st.button("🚪 Logout", key="eco_admin_logout", use_container_width=True):
            logout()
            st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)
