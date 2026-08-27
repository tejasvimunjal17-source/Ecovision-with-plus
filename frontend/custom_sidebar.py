"""
frontend/custom_sidebar.py
-----------------------------
A Gmail/Drive-style collapsible sidebar "drawer" for EcoVision AI.

Ported from LearnMate AI's frontend/custom_sidebar.py. Only the
mechanism (how the drawer opens/closes) was reused as-is; branding was
swapped to EcoVision AI (emerald glow instead of violet) and internal
widget keys were renamed from the `lm_` prefix to `eco_` so nothing in
this codebase references LearnMate naming.

PHASE 1 UPDATE -- dual drawer spec (user vs. admin)
----------------------------------------------------
Mirrors LearnMate's own frontend/custom_sidebar.py, which supports two
independent drawers (the regular user sidebar and the separate Admin
Panel sidebar) sharing this one CSS-generation implementation via a
small `_SidebarSpec` dataclass, but with entirely separate
st.session_state keys and widget-key prefixes so opening/closing one
has zero effect on the other.

render_custom_sidebar_controls() -- UNCHANGED name/signature/behavior,
still the regular (citizen/officer) drawer, still keyed on
st.session_state["sidebar_open"].

render_admin_sidebar_controls() -- NEW. Same mechanism, shield icon,
cyan glow (matching EcoVision's teal/cyan accent palette instead of
emerald, so the two drawers are visually distinguishable), and its own
independent st.session_state["admin_sidebar_open"] key.

Per frontend/user_shell.py / frontend/admin_shell.py (called from
utils.helpers.load_css(), see that file's docstring), at most ONE of
these two functions runs on any given page load -- whichever matches
the signed-in user's role -- so there is no risk of both drawers'
fixed-position toggle buttons / backdrops being mounted at once.

This does NOT touch EcoVision's routing or backend logic in any way:
it only repositions/animates Streamlit's own native sidebar container
via CSS, and (new in Phase 1) hides Streamlit's own auto-generated
page-nav LIST inside that container so frontend/user_shell.py and
frontend/admin_shell.py can render a role-filtered navigation list in
its place -- see the `[data-testid="stSidebarNav"]` rule below. No
pages were added, removed, or reordered; st.page_link()/st.switch_page()
navigation to every existing page in pages/ continues to work exactly
as before (deep links, browser back/forward, direct URLs are all
untouched) -- only the *auto-built, unfiltered* link list that
Streamlit normally renders inside the sidebar is hidden, since that
list is what exposed admin-only and citizen-only pages to every
visitor regardless of role.

How it works (read before touching this file)
------------------------------------------------
Streamlit provides no public API to resize, hide, or animate its own
sidebar - so a custom collapsible sidebar necessarily has to reach it via
CSS targeting Streamlit's own DOM. This file does exactly that, and ONLY
that: no JavaScript, no click simulation, no reading/writing Streamlit's
internal JS state, no iframe.

Why `position: fixed` + `transform`, not a width animation
-------------------------------------------------------------
An earlier version of this file animated the sidebar's `width` between
0 and its normal value. That produced a partially-visible "sliver" bug:
Streamlit's actual sidebar/main layout isn't guaranteed to be sized
purely by that one CSS property (it may involve an inner content wrapper
with its own intrinsic width, or a CSS Grid track sized independently of
the section's own `width`) - so shrinking `width` alone didn't fully
match what the layout engine reserved space for.

`position: fixed` sidesteps that entirely: once an element is taken out
of the normal document flow, no grid/flexbox sizing algorithm affects it
anymore - it becomes an independent floating layer, and `transform:
translateX()` slides that whole layer (identical width at all times, so
nothing inside it "shrinks" or "clips") fully on/off screen. This is a
layout-independent technique, not dependent on which internal layout
model this particular Streamlit version uses.

Because the sidebar is no longer part of the flex/grid flow, main
content no longer reflows into its space automatically - so on desktop
this file also sets an explicit `margin-left` on the main content
container, toggled in sync with the same transition. On mobile, the
drawer instead overlays on top of the content (no margin shift), with a
tap-to-close backdrop - matching how the Gmail/Drive Android drawer
behaves.

The only Streamlit-internal selectors touched are:

    section[data-testid="stSidebar"]         - the sidebar, repositioned
                                                fixed + slid via transform
    section[data-testid="stMain"], .main     - main content, margin-left
                                                + width animated on desktop
    [data-testid="collapsedControl"],
    [data-testid="stSidebarCollapseButton"]  - Streamlit's own native
                                                collapse arrow, hidden
                                                (display:none) since our
                                                toggle button replaces it
    [data-testid="stSidebarNav"]             - Streamlit's own AUTO-BUILT
                                                page-nav list (new in
                                                Phase 1: hidden so the
                                                role-filtered nav rendered
                                                by frontend/user_shell.py
                                                or frontend/admin_shell.py
                                                takes its place instead)
    .block-container                         - given a small top-padding
                                                reservation so the fixed
                                                toggle button (top-left)
                                                never overlaps EcoVision's
                                                existing page content in
                                                the closed state

Everything ELSE that's rendered inside `with st.sidebar:` (by
frontend/user_shell.py or frontend/admin_shell.py) is completely
untouched by this file -- nothing is moved out of st.sidebar.

State
------
st.session_state["sidebar_open"] (user drawer) and
st.session_state["admin_sidebar_open"] (admin drawer) are the single
sources of truth (default True each). No JavaScript state, no browser
storage - plain Python booleans, recomputed into CSS on every rerun.
"""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

_DRAWER_WIDTH = "21rem"
_DRAWER_WIDTH_MOBILE = "min(21rem, 85vw)"
_TRANSITION_MS = 300


@dataclass(frozen=True)
class _SidebarSpec:
    state_key: str      # st.session_state key holding open/closed (bool)
    key_prefix: str      # Streamlit widget key prefix (must be unique per sidebar)
    icon: str             # toggle button glyph
    glow: str             # box-shadow color (rest state)
    glow_hover: str       # box-shadow color (hover state)


# EcoVision AI brand glow (emerald, #10b981) for the regular user drawer --
# matches the rest of the app's existing button/hover glow already defined
# in assets/style.css.
USER_SIDEBAR = _SidebarSpec(
    state_key="sidebar_open",
    key_prefix="eco_drawer",
    icon="\U0001F30E",
    glow="rgba(16,185,129,0.30)",
    glow_hover="rgba(16,185,129,0.45)",
)

# Cyan/teal glow for the separate Admin Panel drawer -- visually
# distinguishes "you are in the Admin Panel" from the regular emerald
# user shell, using colors already in EcoVision's palette (teal/cyan
# accents), not a new brand color.
ADMIN_SIDEBAR = _SidebarSpec(
    state_key="admin_sidebar_open",
    key_prefix="eco_admin_drawer",
    icon="\U0001F6E1\uFE0F",
    glow="rgba(34,211,238,0.30)",
    glow_hover="rgba(34,211,238,0.45)",
)


def _render_drawer(spec: _SidebarSpec) -> None:
    """Render one drawer's toggle button, mobile backdrop, and CSS. Shared
    implementation behind both public functions below - see _SidebarSpec
    for what actually varies between the user and admin drawers."""
    st.session_state.setdefault(spec.state_key, True)
    is_open = st.session_state[spec.state_key]

    toggle_container_key = f"{spec.key_prefix}_toggle"
    toggle_btn_key = f"{spec.key_prefix}_toggle_btn"
    backdrop_container_key = f"{spec.key_prefix}_backdrop"
    backdrop_btn_key = f"{spec.key_prefix}_backdrop_btn"

    # ---- Toggle button: always visible, always in the same spot. ----
    with st.container(key=toggle_container_key):
        toggle_clicked = st.button(
            spec.icon, key=toggle_btn_key, help="Open / Close Navigation"
        )

    # ---- Mobile tap-to-close backdrop: a real (always-rendered) button,
    # shown only via a CSS media query on small screens and only while the
    # drawer is open. Clicking it closes the drawer, same as tapping
    # outside a Gmail/Drive Android drawer. ----
    with st.container(key=backdrop_container_key):
        backdrop_clicked = st.button(
            "", key=backdrop_btn_key, help="Close navigation"
        )

    if toggle_clicked or (backdrop_clicked and is_open):
        st.session_state[spec.state_key] = not st.session_state[spec.state_key]
        is_open = st.session_state[spec.state_key]

    transform = "translateX(0)" if is_open else "translateX(-100%)"
    backdrop_display = "block" if is_open else "none"
    main_margin = _DRAWER_WIDTH if is_open else "0"

    st.markdown(
        f"""
        <style>
        /* ---- Fixed toggle button: always visible, always in the same
        spot, regardless of the drawer's open/closed state. ---- */
        div[class*="st-key-{toggle_container_key}"] {{
            position: fixed;
            top: 14px;
            left: 14px;
            z-index: 1000000;
        }}
        div[class*="st-key-{toggle_btn_key}"] button {{
            width: 44px;
            height: 44px;
            border-radius: 14px;
            padding: 0;
            font-size: 1.2rem;
            box-shadow: 0 6px 18px {spec.glow};
            transition: transform 280ms ease, box-shadow 280ms ease;
        }}
        div[class*="st-key-{toggle_btn_key}"] button:hover {{
            transform: translateY(-2px) scale(1.05);
            box-shadow: 0 10px 24px {spec.glow_hover};
        }}

        /* ---- The drawer itself: taken out of document flow so no
        grid/flex sizing algorithm can partially-clip it - always full
        width, purely slid on/off screen via transform. ---- */
        section[data-testid="stSidebar"] {{
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            height: 100vh !important;
            width: {_DRAWER_WIDTH} !important;
            min-width: {_DRAWER_WIDTH} !important;
            max-width: {_DRAWER_WIDTH} !important;
            z-index: 999998;
            overflow-y: auto !important;
            transform: {transform};
            transition: transform {_TRANSITION_MS}ms ease;
        }}
        @media (max-width: 640px) {{
            section[data-testid="stSidebar"] {{
                width: {_DRAWER_WIDTH_MOBILE} !important;
                min-width: {_DRAWER_WIDTH_MOBILE} !important;
                max-width: {_DRAWER_WIDTH_MOBILE} !important;
            }}
        }}

        /* ---- Desktop only: main content margin AND width both shift in
        sync with the drawer, since the sidebar is position:fixed (out of
        flex flow) and stMain would otherwise stay full-width and overflow
        past the right edge when margin-left alone were applied. ---- */
        @media (min-width: 641px) {{
            section[data-testid="stMain"], .main {{
                margin-left: {main_margin} !important;
                width: calc(100% - {main_margin}) !important;
                max-width: calc(100% - {main_margin}) !important;
                box-sizing: border-box !important;
                transition: margin-left {_TRANSITION_MS}ms ease, width {_TRANSITION_MS}ms ease;
            }}
        }}

        /* ---- Defensive safety net: prevent any transient horizontal
        scrollbar/1px rounding artifact during the open/close transition
        (belt-and-braces alongside the calc() fix above -- does not
        change any visual sizing on its own). ---- */
        html, body, .stApp, div[data-testid="stAppViewContainer"] {{
            overflow-x: hidden;
        }}

        /* ---- Mobile tap-to-close backdrop: invisible/inert on desktop,
        a dim full-screen tap target on mobile while the drawer is open. ---- */
        div[class*="st-key-{backdrop_container_key}"] {{
            display: none;
        }}
        @media (max-width: 640px) {{
            div[class*="st-key-{backdrop_container_key}"] {{
                display: {backdrop_display};
                position: fixed;
                inset: 0;
                z-index: 999997;
            }}
            div[class*="st-key-{backdrop_btn_key}"] button {{
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.45) !important;
                border: none !important;
                box-shadow: none !important;
                cursor: pointer;
            }}
        }}

        /* ---- Hide the GitHub / Share / star / fork icon cluster in
        Streamlit's toolbar (top-right). Multiple selectors are targeted
        since the exact data-testid has varied across Streamlit
        versions; this is purely cosmetic (display:none) and does not
        remove any app functionality -- the "settings/rerun" menu
        (#MainMenu) is intentionally left untouched. ---- */
        div[data-testid="stToolbarActions"] {{
            display: none !important;
        }}
        .stAppDeployButton {{
            display: none !important;
        }}

        /* ---- Hide Streamlit's own native collapse control - fully
        replaced by our toggle button above. Presentational display:none
        only, not a click or a state read. ---- */
        div[data-testid="stSidebarCollapseButton"],
        div[data-testid="collapsedControl"] {{
            display: none !important;
        }}

        /* ---- PHASE 1: hide Streamlit's own auto-generated page-nav
        list (the unfiltered list of every file in pages/, previously
        visible to every visitor regardless of role). This is a pure
        display:none on the navigation WIDGET -- it does not disable,
        move, or rename a single route: st.page_link()/st.switch_page()
        to any of these same page files (used by frontend/user_shell.py,
        frontend/admin_shell.py, and every existing st.switch_page() call
        already in the codebase, e.g. pages/1_Login.py's post-login
        redirect) still work exactly as before, and every page's own
        require_login()/role check is completely unaffected -- this only
        controls which links visually render in the sidebar, not which
        pages are reachable or protected. ---- */
        div[data-testid="stSidebarNav"] {{
            display: none !important;
        }}

        /* ---- Reserve top-left clearance so the fixed toggle button
        never overlaps EcoVision's existing page content (e.g. the
        "EcoVision AI" header row on the Home page) when the drawer is
        closed. This is the ONLY new spacing rule added for integration -
        every other existing style in assets/style.css is untouched. ---- */
        .block-container {{
            padding-top: 4.5rem !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_custom_sidebar_controls() -> None:
    """Render the drawer toggle, the mobile tap-to-close backdrop, and
    apply the resulting open/closed CSS, for the regular (citizen/officer)
    user app.

    Call this once, early on every page (it's wired into
    utils.helpers.load_css(), which every page already calls) - both the
    toggle button and the backdrop are independent, fixed-position
    elements, so they don't need to live inside `st.sidebar` to work.

    Unchanged from before this file was extended to support the Admin
    Panel drawer too - same name, same signature, same behavior, same
    st.session_state["sidebar_open"] key.
    """
    _render_drawer(USER_SIDEBAR)


def render_admin_sidebar_controls() -> None:
    """The Admin Panel's equivalent of render_custom_sidebar_controls():
    same collapsible-drawer mechanism, but with the shield icon, a cyan
    glow, and its own independent st.session_state["admin_sidebar_open"]
    key and widget-key prefix - opening/closing this one has no effect on
    the regular user sidebar's state, and vice versa.

    Call this once, early, in place of render_custom_sidebar_controls()
    when the signed-in user's role is "admin" (see utils.helpers.load_css()
    for the exact call-site logic) - same placement rule as the user
    version.
    """
    _render_drawer(ADMIN_SIDEBAR)
