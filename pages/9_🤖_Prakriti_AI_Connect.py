import streamlit as st
from chatbot.prakriti import stream_reply, save_message, load_history, clear_history
from utils.helpers import load_css, init_session_state
from config import settings

st.set_page_config(page_title="Prakriti AI Connect | EcoVision AI", page_icon="🌿", layout="wide")
init_session_state()
load_css()

st.markdown(
    '<div class="eco-hero"><h1>🌿 Prakriti AI Connect</h1>'
    '<p>Your 24×7 bilingual AI Sustainability Assistant — ask about waste segregation, '
    'recycling, composting, e-waste, MCG guidelines, or your complaints.</p></div>',
    unsafe_allow_html=True,
)

if not settings.is_ai_configured():
    st.warning("⚠️ Running in demo mode — add a real `OPENROUTER_API_KEY` to `.env` for live AI responses.")

user = st.session_state.get("user")
user_id = user["id"] if user else 0
session_id = st.session_state["chat_session_id"]

top1, top2, top3 = st.columns([2, 1, 1])
with top1:
    language = st.radio("Language / भाषा", ["English", "हिंदी (Hindi)"], horizontal=True)
with top2:
    if st.button("🗑️ Clear Chat", use_container_width=True):
        if user:
            clear_history(user_id, session_id)
        st.session_state["chat_history"] = []
        st.rerun()
with top3:
    st.caption("💬 Available on every page")

# Load persisted history for logged-in users
if user and not st.session_state.get("chat_history"):
    st.session_state["chat_history"] = load_history(user_id, session_id)

if not st.session_state["chat_history"]:
    st.session_state["chat_history"] = [{
        "role": "assistant",
        "content": "🌿 Namaste! I'm Prakriti AI Connect. Ask me about waste segregation, "
                   "recycling, composting, e-waste disposal, or MCG guidelines — in English or Hindi!"
    }]

chat_container = st.container(height=480)
with chat_container:
    for msg in st.session_state["chat_history"]:
        css_class = "chat-bubble-user" if msg["role"] == "user" else "chat-bubble-ai"
        icon = "🧑" if msg["role"] == "user" else "🌿"
        st.markdown(f'<div class="{css_class}">{icon} {msg["content"]}</div>', unsafe_allow_html=True)

user_input = st.chat_input("Ask Prakriti AI Connect anything about sustainability...")

if user_input:
    st.session_state["chat_history"].append({"role": "user", "content": user_input})
    if user:
        save_message(user_id, session_id, "user", user_input)

    with chat_container:
        st.markdown(f'<div class="chat-bubble-user">🧑 {user_input}</div>', unsafe_allow_html=True)
        placeholder = st.empty()
        full_response = ""
        for chunk in stream_reply(st.session_state["chat_history"][:-1], user_input, language):
            full_response += chunk
            placeholder.markdown(f'<div class="chat-bubble-ai">🌿 {full_response}▌</div>', unsafe_allow_html=True)
        placeholder.markdown(f'<div class="chat-bubble-ai">🌿 {full_response}</div>', unsafe_allow_html=True)

    st.session_state["chat_history"].append({"role": "assistant", "content": full_response})
    if user:
        save_message(user_id, session_id, "assistant", full_response)
    st.rerun()

st.markdown("---")
st.caption("Prakriti AI Connect only assists with waste, recycling, sustainability and civic topics related to this platform.")
