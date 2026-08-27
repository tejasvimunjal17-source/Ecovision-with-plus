"""
frontend/styles.py
---------------------
PHASE 1 — Additive LearnMate-inspired design-token layer for EcoVision AI.

This is intentionally a NEW, ADDITIVE stylesheet, not a replacement for
assets/style.css. Every existing class used across the 17 pages in
pages/ (`eco-hero`, `eco-card`, `eco-pill`, `eco-stat`, `eco-section-title`,
`eco-section-sub`, `eco-footer`, `chat-bubble-user`, `chat-bubble-ai`, and
the inline-styled `status_badge()`/`priority_badge()` spans in
utils/helpers.py) keeps working completely unchanged — this file is
injected IN ADDITION to assets/style.css (see utils.helpers.load_css()),
never instead of it. Nothing here overrides those selectors.

What this file DOES define is a small set of NEW classes used only by
the Phase 1 shell components (frontend/user_shell.py,
frontend/admin_shell.py, frontend/chatbot_widget.py, components/ui.py):
the sidebar nav-link/active-pill treatment, the shell brand header, and
the floating Prakriti AI chatbot widget — modeled on LearnMate AI's
frontend/styles.py (glassmorphism cards, gradient buttons/pills,
Space Grotesk + Inter + JetBrains Mono type system) but recolored to
EcoVision's own environmental identity:

    Ink Navy   #0B1220   (dark surface base, deeper than LearnMate's
                          #0F1229 to read as "night city" rather than
                          "night sky")
    Emerald    #10B981   (primary accent — EcoVision's existing button
                          color, reused here as the anchor of the new
                          gradient rather than replaced)
    Teal       #22D3B0   (secondary accent)
    Cyan       #22D3EE   (tertiary accent — used for the Admin Panel
                          drawer/shell, see frontend/custom_sidebar.py,
                          so Admin Panel is visually distinct from the
                          emerald/teal user shell)

No page redesign happens in Phase 1 — this file is loaded by every page
(via utils.helpers.load_css()) but only its shell-scoped classes are
actually used yet; the rest sits ready for the incremental per-page
migration in later phases.
"""

from __future__ import annotations

import streamlit as st

FONT_IMPORT = (
    "https://fonts.googleapis.com/css2?"
    "family=Space+Grotesk:wght@500;600;700&"
    "family=Inter:wght@400;500;600;700&"
    "family=JetBrains+Mono:wght@500;600&display=swap"
)


def inject_shell_css() -> None:
    """Inject the Phase 1 shell design-token stylesheet.

    IMPORTANT: st.markdown() runs its input through a Markdown parser
    before rendering the HTML. Any line indented 4+ spaces is treated as
    a Markdown *code block* and gets escaped/printed as literal text
    instead of being interpreted as HTML — this is what causes raw CSS to
    "leak" onto the page above the UI. To guarantee that never happens,
    the CSS below is built with normal (readable) Python indentation,
    then every line's leading whitespace is stripped right before
    injection — same safeguard LearnMate's frontend/styles.py uses. CSS
    itself doesn't care about indentation, so this is purely a rendering
    safeguard, not a formatting choice.
    """
    st.markdown(f'<link rel="stylesheet" href="{FONT_IMPORT}">', unsafe_allow_html=True)

    raw_css = """
        :root {
            --eco2-bg: #0B1220;
            --eco2-surface: rgba(255,255,255,0.045);
            --eco2-surface-border: rgba(255,255,255,0.09);
            --eco2-text: #EAF6F0;
            --eco2-text-muted: #93A5A0;
            --eco2-emerald: #10B981;
            --eco2-teal: #22D3B0;
            --eco2-cyan: #22D3EE;
            --eco2-gradient: linear-gradient(120deg, #10B981 0%, #22D3B0 100%);
            --eco2-gradient-admin: linear-gradient(120deg, #0EA5A4 0%, #22D3EE 100%);
            --eco2-radius: 18px;
            --eco2-shadow: 0 8px 30px rgba(0,0,0,0.35);
        }

        /* ---------- Shell brand header (sidebar top) ---------- */
        .eco-shell-brand {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 1.3rem;
            font-weight: 700;
            letter-spacing: -0.01em;
            color: var(--eco2-text);
            margin-bottom: 0;
        }
        .eco-shell-subtitle {
            font-family: 'Inter', sans-serif;
            font-size: 0.85rem;
            color: var(--eco2-text-muted);
            margin-top: 2px;
        }
        .eco-shell-role-pill {
            display: inline-block;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.68rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--eco2-teal);
            background: rgba(34,211,176,0.12);
            border: 1px solid rgba(34,211,176,0.3);
            padding: 2px 9px;
            border-radius: 100px;
            margin-left: 6px;
        }

        /* ---------- Sidebar nav links (user & admin shells) ---------- */
        .eco-nav-section-label {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.7rem;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: var(--eco2-text-muted);
            margin: 1rem 0 0.35rem 0.2rem;
        }
        /* st.page_link renders as an <a> inside a stPageLink container;
        Streamlit marks the link to the CURRENT page with
        aria-current="page" automatically, so the active-state gradient
        pill below needs no manual "which page am I on" tracking. */
        div[data-testid="stPageLink"] a {
            border-radius: 12px !important;
            padding: 0.5rem 0.8rem !important;
            margin: 2px 0 !important;
            font-family: 'Inter', sans-serif !important;
            font-weight: 500 !important;
            transition: background-color 0.18s ease !important;
        }
        div[data-testid="stPageLink"] a:hover {
            background-color: rgba(16,185,129,0.14) !important;
        }
        div[data-testid="stPageLink"] a[aria-current="page"] {
            background: var(--eco2-gradient) !important;
            color: white !important;
            font-weight: 600 !important;
            box-shadow: 0 6px 18px rgba(16,185,129,0.35) !important;
        }
        div[data-testid="stPageLink"] a[aria-current="page"] p {
            color: white !important;
        }
        /* Admin Panel variant: same mechanism, cyan gradient instead of
        emerald, scoped to a wrapper class set by frontend/admin_shell.py
        so it never affects the regular user sidebar's nav links. */
        .eco-admin-nav div[data-testid="stPageLink"] a:hover {
            background-color: rgba(34,211,238,0.14) !important;
        }
        .eco-admin-nav div[data-testid="stPageLink"] a[aria-current="page"] {
            background: var(--eco2-gradient-admin) !important;
            box-shadow: 0 6px 18px rgba(34,211,238,0.35) !important;
        }

        /* ---------- Glassmorphism card (new, additive — does not
        replace .eco-card) ---------- */
        .eco-glass-card {
            background: var(--eco2-surface);
            border: 1px solid var(--eco2-surface-border);
            border-radius: var(--eco2-radius);
            box-shadow: var(--eco2-shadow);
            padding: 1.4rem;
        }

        /* ---------- Floating Prakriti AI chatbot widget ----------
        Scoped entirely to its own container key (set in
        frontend/chatbot_widget.py) so nothing here leaks onto any other
        button/container on the page — same technique LearnMate AI uses
        for its own floating chatbot (div[class*="st-key-lm_chatbot"]). */
        div[class*="st-key-eco_prakriti_widget"] {
            position: fixed;
            right: 20px;
            bottom: 20px;
            z-index: 999995;
            width: min(380px, 92vw);
        }
        div[class*="st-key-eco_prakriti_panel"] {
            background: var(--eco2-bg);
            border: 1px solid var(--eco2-surface-border);
            border-radius: var(--eco2-radius);
            box-shadow: 0 16px 40px rgba(0,0,0,0.35);
            padding: 1rem;
        }
        div[class*="st-key-eco_prakriti_launcher_btn"] button {
            border-radius: 999px !important;
            width: 56px;
            height: 56px;
            font-size: 1.4rem;
            box-shadow: 0 6px 18px rgba(16,185,129,0.35) !important;
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }
        div[class*="st-key-eco_prakriti_launcher_btn"] button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 24px rgba(16,185,129,0.45) !important;
        }
        @media (max-width: 480px) {
            div[class*="st-key-eco_prakriti_widget"] {
                right: 10px;
                bottom: 10px;
                width: 92vw;
            }
        }
        /* ---------- PHASE 3A: "Get Started" auth-choice popup ----------
        Rendered inside a native st.dialog (app.py, _render_auth_choice_
        dialog). st.dialog already supplies the dark modal chrome, rounded
        corners, backdrop and responsive desktop/mobile sizing consistent
        with the rest of the app — this block only styles the two choice
        buttons + subtitle + cancel button inside it, reusing the same
        --eco2-radius/--eco2-shadow tokens as the rest of this file rather
        than introducing new ones. Modeled on LearnMate AI's own
        .lm-auth-choice-* block (frontend/styles.py) — same layout/
        structure, same white "neutral SaaS pill" choice-button treatment
        matching the reference screenshot, recolored hover state to
        EcoVision's emerald/cyan instead of LearnMate's violet. */
        .eco-auth-choice-sub {
            text-align: center;
            color: var(--eco2-text-muted);
            font-size: 0.92rem;
            line-height: 1.5;
            margin: -0.2rem 0 1.2rem 0;
        }
        .eco-auth-choice-buttons {
            display: flex;
            flex-direction: column;
            gap: 0.8rem;
            margin-bottom: 0.4rem;
        }
        .eco-auth-choice-buttons div[class*="st-key-auth_choice_google"] button,
        .eco-auth-choice-buttons div[class*="st-key-auth_choice_email"] button {
            background: #FFFFFF !important;
            color: #0B1220 !important;
            border: 1px solid rgba(0,0,0,0.06) !important;
            border-radius: var(--eco2-radius) !important;
            padding: 0.85rem 1.2rem !important;
            font-size: 1rem !important;
            font-weight: 600 !important;
            box-shadow: 0 6px 18px rgba(0,0,0,0.18);
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }
        .eco-auth-choice-buttons div[class*="st-key-auth_choice_google"] button:hover,
        .eco-auth-choice-buttons div[class*="st-key-auth_choice_email"] button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 26px rgba(0,0,0,0.26);
        }
        .eco-auth-choice-close {
            margin-top: 0.6rem;
        }
        .eco-auth-choice-close div[class*="st-key-auth_choice_close"] button {
            background: transparent !important;
            color: var(--eco2-text-muted) !important;
            border: 1px solid var(--eco2-surface-border) !important;
            box-shadow: none !important;
            font-weight: 500 !important;
        }
        .eco-auth-choice-close div[class*="st-key-auth_choice_close"] button:hover {
            color: var(--eco2-text) !important;
            border-color: var(--eco2-cyan) !important;
            transform: none;
            box-shadow: none !important;
        }
        @media (max-width: 480px) {
            .eco-auth-choice-buttons div[class*="st-key-auth_choice_google"] button,
            .eco-auth-choice-buttons div[class*="st-key-auth_choice_email"] button {
                padding: 0.8rem 1rem !important;
                font-size: 0.95rem !important;
            }
        }

    """
    css = "\n".join(line.lstrip() for line in raw_css.splitlines())
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
