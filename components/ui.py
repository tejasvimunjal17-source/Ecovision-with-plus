"""
components/ui.py
--------------------
PHASE 1 — minimal, reusable UI primitives shared by the new shell files
(frontend/user_shell.py, frontend/admin_shell.py). Deliberately small:
per the Phase 1 scope, this is foundation only, not a full component
library for redesigning all 17 pages (that migration happens
incrementally in a later phase, reusing/extending these same helpers).

Every function here is presentation-only — none of them read or write
anything in backend/, database/, or chatbot/.
"""

from __future__ import annotations

import streamlit as st


def sidebar_brand(title: str, subtitle: str | None = None, role_label: str | None = None) -> None:
    """Renders the small branded header at the top of a sidebar shell,
    e.g. "EcoVision AI" + "Hi, Priya" + a "CITIZEN" role pill.

    Uses the .eco-shell-brand / .eco-shell-subtitle / .eco-shell-role-pill
    classes defined in frontend/styles.py (additive — does not touch
    assets/style.css)."""
    role_html = f'<span class="eco-shell-role-pill">{role_label}</span>' if role_label else ""
    st.markdown(
        f'<div class="eco-shell-brand">{title}{role_html}</div>',
        unsafe_allow_html=True,
    )
    if subtitle:
        st.markdown(f'<div class="eco-shell-subtitle">{subtitle}</div>', unsafe_allow_html=True)


def nav_section_label(text: str) -> None:
    """A small uppercase section label above a group of sidebar nav
    links, e.g. "NAVIGATION" or "ACCOUNT"."""
    st.markdown(f'<div class="eco-nav-section-label">{text}</div>', unsafe_allow_html=True)
