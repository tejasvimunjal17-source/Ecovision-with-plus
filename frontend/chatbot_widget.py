"""
frontend/chatbot_widget.py
------------------------------
PHASE 1 — a floating, bottom-right "Prakriti AI" launcher + chat panel,
rendered on every authenticated (non-admin) User Dashboard page —
LearnMate AI's floating "AI Mentor" widget is the direct visual/UX
reference (frontend/chatbot.py in the LearnMate codebase).

PROTECTED BACKEND — nothing changed
----------------------------------------
This file is a UI WRAPPER ONLY. It imports and calls the exact same,
untouched functions pages/9_🤖_Prakriti_AI_Connect.py already uses:

    stream_reply(history, user_message, language)   -- chatbot/prakriti.py
    save_message(user_id, session_id, role, message) -- chatbot/prakriti.py
    load_history(user_id, session_id)                -- chatbot/prakriti.py
    clear_history(user_id, session_id)                -- chatbot/prakriti.py

...with the exact same session-state keys pages/9 already relies on:

    st.session_state["chat_history"]     -- list of {"role", "content"}
    st.session_state["chat_session_id"]  -- stamped once per browser
                                             session in
                                             utils.helpers.init_session_state()

No new persistence mechanism, no new session-state keys for chat data,
no change to chatbot/prakriti.py itself. This widget and
pages/9_🤖_Prakriti_AI_Connect.py both read/write the SAME history for
the same signed-in user + session, so a message sent in one is visible
in the other — they are two views onto one conversation, not two
separate chats. pages/9 itself is left in place, unmodified, per this
phase's scope ("do NOT delete it in Phase 1").

Visibility (see utils.helpers.load_css() call-site logic)
----------------------------------------------------------------
Mounted only when a NON-admin user is signed in — i.e. never on the
public landing page, Login, Register, or the Admin Panel. The Admin
Panel's own chatbot visibility is an explicit, separate decision left
for a later phase (see frontend/admin_shell.py).
"""

from __future__ import annotations

import streamlit as st

from chatbot.prakriti import stream_reply, save_message, load_history, clear_history
from config import settings

_LAUNCHER_KEY = "eco_prakriti_launcher_btn"


def render_prakriti_widget(user: dict) -> None:
    """Render the floating Prakriti AI launcher (always) and, when
    expanded, the chat panel. Call once per authenticated non-admin
    page load, from utils.helpers.load_css()."""
    st.session_state.setdefault("show_chat", False)

    user_id = user["id"]
    session_id = st.session_state["chat_session_id"]

    with st.container(key="eco_prakriti_widget"):
        if not st.session_state["show_chat"]:
            if st.button("🌿", key=_LAUNCHER_KEY, help="Chat with Prakriti AI"):
                st.session_state["show_chat"] = True
                st.rerun()
            return

        with st.container(key="eco_prakriti_panel"):
            top1, top2, top3 = st.columns([2, 1, 1])
            with top1:
                st.markdown("**🌿 Prakriti AI**")
            with top2:
                language = st.radio(
                    "Language", ["English", "हिंदी"], horizontal=True,
                    label_visibility="collapsed", key="eco_prakriti_lang",
                )
            with top3:
                if st.button("✕", key="eco_prakriti_close", help="Close"):
                    st.session_state["show_chat"] = False
                    st.rerun()

            if not settings.is_ai_configured():
                st.caption("⚠️ Demo mode — add OPENROUTER_API_KEY for live AI replies.")

            if not st.session_state.get("chat_history"):
                st.session_state["chat_history"] = load_history(user_id, session_id) or [{
                    "role": "assistant",
                    "content": "🌿 Namaste! Ask me about waste segregation, recycling, "
                               "composting, e-waste, or your complaints — English or Hindi.",
                }]

            chat_box = st.container(height=280)
            with chat_box:
                for msg in st.session_state["chat_history"]:
                    css_class = "chat-bubble-user" if msg["role"] == "user" else "chat-bubble-ai"
                    icon = "🧑" if msg["role"] == "user" else "🌿"
                    st.markdown(f'<div class="{css_class}">{icon} {msg["content"]}</div>', unsafe_allow_html=True)

            user_input = st.chat_input("Ask Prakriti AI...", key="eco_prakriti_input")
            clear_clicked = st.button("🗑️ Clear chat", key="eco_prakriti_clear", use_container_width=True)

            if clear_clicked:
                clear_history(user_id, session_id)
                st.session_state["chat_history"] = []
                st.rerun()

            if user_input:
                # Language label passed to stream_reply matches exactly
                # what pages/9 passes ("English" / "हिंदी (Hindi)") --
                # chatbot/prakriti.get_system_prompt() only checks whether
                # the string starts with "hi", so the shorter "हिंदी"
                # label used here resolves identically.
                language_full = "हिंदी (Hindi)" if language == "हिंदी" else "English"

                st.session_state["chat_history"].append({"role": "user", "content": user_input})
                save_message(user_id, session_id, "user", user_input)

                with chat_box:
                    st.markdown(f'<div class="chat-bubble-user">🧑 {user_input}</div>', unsafe_allow_html=True)
                    placeholder = st.empty()
                    full_response = ""
                    for chunk in stream_reply(st.session_state["chat_history"][:-1], user_input, language_full):
                        full_response += chunk
                        placeholder.markdown(f'<div class="chat-bubble-ai">🌿 {full_response}▌</div>', unsafe_allow_html=True)
                    placeholder.markdown(f'<div class="chat-bubble-ai">🌿 {full_response}</div>', unsafe_allow_html=True)

                st.session_state["chat_history"].append({"role": "assistant", "content": full_response})
                save_message(user_id, session_id, "assistant", full_response)
                st.rerun()
