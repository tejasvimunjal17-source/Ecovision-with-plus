"""
app.py
--------
EcoVision AI — Smart Waste Management & Recycling in Indian Cities
Main entry point: premium landing page (logged out) / role-based
redirect hint (logged in). Streamlit auto-builds sidebar navigation
from the numbered files inside pages/.

PHASE 3B: also the landing spot for Google OIDC's redirect-back (see
the "Google OIDC account linking" block below) — st.login() always
returns the browser here, since this is the only page that ever calls
it (frontend/... auth dialog is defined and used entirely within this
file, see _render_auth_choice_dialog()).
"""
import streamlit as st
from database.db import init_db, ConfigurationError
from utils.helpers import load_css, init_session_state, google_signed_in
from config import settings

st.set_page_config(
    page_title="EcoVision AI | Smart Waste Management",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# PHASE 2B: init_db() now opens a real network connection to Supabase
# (see database/db.py's docstring) instead of touching a local SQLite
# file, so it can fail — a missing/misconfigured SUPABASE_DB_URL, or the
# database being unreachable. Catching ConfigurationError here and
# showing a clear st.error() + st.stop() (rather than letting an
# uncaught psycopg2/ConfigurationError surface as a raw Streamlit
# traceback) is exactly the "clear configuration error, not an obscure
# database error" this phase's instructions asked for. Same guard is
# also in utils.helpers.init_session_state() below, for the same reason
# on every other page (see that function's own comment).
try:
    init_db()
except ConfigurationError as e:
    st.error(f"⚠️ EcoVision AI can't reach its database.\n\n{e}")
    st.stop()

init_session_state()
load_css()

# ------------------------------------------------------------------
# PHASE 3B — Google OIDC account linking
# ------------------------------------------------------------------
# The moment Streamlit's own OIDC session (st.user) reports a signed-in
# Google identity but EcoVision's OWN session
# (st.session_state["user"]) doesn't know about it yet, look up (or, on
# this visitor's first Google sign-in, create) the matching EcoVision
# account via backend.auth.find_or_create_google_user() and adopt it as
# st.session_state["user"] — the exact same session key every existing
# page's require_login() already reads (utils/helpers.py), so NO page
# needs to know Google sign-in exists; find_or_create_google_user()
# returns the identical (True, user_dict)/(False, message) shape
# login_user() already does, and the redirect-by-role dict below is the
# same mapping pages/1_🔐_Login.py's own email-login success path
# already uses (duplicated here, not imported, so this block never has
# to modify that page — see this phase's completion report for that
# trade-off).
#
# This only runs on that ONE linking rerun: once
# st.session_state["user"] is set, this block's own `if` condition is
# already False on every later rerun, so an already-signed-in Google
# visitor never re-hits the database on every page load — satisfies
# "idempotent, no duplicate lookups/creates".
if not st.session_state.get("user") and google_signed_in():
    from backend.auth import find_or_create_google_user
    google_full_name = st.user.get("name", "") or " ".join(
        filter(None, [st.user.get("given_name", ""), st.user.get("family_name", "")])
    )
    ok, result = find_or_create_google_user(email=st.user.get("email", ""), full_name=google_full_name)
    if ok:
        st.session_state["user"] = result
        from utils.helpers import toast
        toast(f"Welcome, {result['full_name']}!")
        target = {
            "citizen": "pages/3_🏠_Citizen_Dashboard.py",
            "officer": "pages/7_🧑‍💼_Officer_Dashboard.py",
            "admin": "pages/8_🛠️_Admin_Dashboard.py",
        }[result["role"]]
        st.switch_page(target)
    else:
        # Surfaced once, right below the top nav further down — st.user
        # stays signed in (Google's own cookie), so the visitor can just
        # retry (e.g. a transient DB hiccup) without going through
        # Google's consent screen again.
        st.session_state["_google_link_error"] = result


# ---------------------------------------------------------------
# PHASE 3A/3B — "Get Started" auth-choice popup
# ---------------------------------------------------------------
# Referenced from LearnMate AI's frontend/landing.py: an intermediate
# method-choice dialog between the landing page's "Get Started" button
# and EcoVision's login/register flow. "Continue with Email" hands off
# unchanged to the existing pages/1_🔐_Login.py / pages/2_📝_Register.py
# flow. "Continue with Google" calls Streamlit's own st.login(); the
# actual Google-identity -> EcoVision-account linking happens in the
# block ABOVE (not here) once Google redirects back to this same
# page — see that block's own comment for why.
st.session_state.setdefault("show_auth_choice", False)


def _close_auth_choice_dialog() -> None:
    """on_dismiss callback (X / Esc / click-outside). Without this, a
    native dismiss would leave show_auth_choice=True, so the very next
    rerun triggered by anything else on the page would silently pop the
    dialog back open — resetting the flag here makes "dismiss" behave
    exactly like the explicit Cancel button below."""
    st.session_state["show_auth_choice"] = False


@st.dialog("🚀 Get Started with EcoVision AI", on_dismiss=_close_auth_choice_dialog)
def _render_auth_choice_dialog() -> None:
    """Auth-method choice popup. This is ONLY a method picker — it does
    not register or log anyone in itself; both branches hand off to
    EcoVision's existing, unmodified auth pages/flow."""
    st.markdown(
        '<p class="eco-auth-choice-sub">Choose how you\'d like to continue. '
        "You can always switch later.</p>",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="eco-auth-choice-buttons">', unsafe_allow_html=True)
    google_clicked = st.button(
        "🅶  Continue with Google  →", use_container_width=True, key="auth_choice_google",
    )
    email_clicked = st.button(
        "✉️  Continue with Email  →", use_container_width=True, key="auth_choice_email",
    )
    st.markdown("</div>", unsafe_allow_html=True)

    if google_clicked:
        # Real Google sign-in via Streamlit's native OIDC support
        # (st.login() — requires an [auth] section in
        # .streamlit/secrets.toml; see supabase/README.md's "Google
        # OIDC configuration" section for the exact keys and a Google
        # Cloud setup walkthrough). This call never returns on success
        # (it raises Streamlit's own internal redirect control flow —
        # the actual EcoVision-account linking happens once Google
        # redirects back to this page, see the block near the top of
        # this file). Anything below only runs if Google Sign-In
        # genuinely isn't configured/reachable on THIS deployment, in
        # which case we say so honestly rather than pretending it
        # worked or faking an account.
        try:
            st.login()
        except Exception as exc:
            st.warning(
                f"Google Sign-In isn't configured on this deployment ({exc}). "
                "Please use **Continue with Email** for now."
            )

    if email_clicked:
        st.session_state["show_auth_choice"] = False
        st.switch_page("pages/2_📝_Register.py")

    st.markdown('<div class="eco-auth-choice-close">', unsafe_allow_html=True)
    if st.button("Cancel", key="auth_choice_close", use_container_width=True):
        st.session_state["show_auth_choice"] = False
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------
# Top nav bar (approximated with columns — Streamlit has no fixed
# navbar, so we keep it compact and always at the top of the page)
# ---------------------------------------------------------------
nav_l, nav_r = st.columns([3, 2])
with nav_l:
    st.markdown("### 🌿 EcoVision AI")
with nav_r:
    if st.session_state.get("user"):
        u = st.session_state["user"]
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**👋 {u['full_name'].split()[0]}** &nbsp;·&nbsp; `{u['role'].title()}`")
        with c2:
            if st.button("Logout", use_container_width=True):
                from utils.helpers import logout
                logout()
                st.rerun()
    else:
        c1, c2 = st.columns(2)
        with c1:
            st.page_link("pages/1_🔐_Login.py", label="Login", icon="🔐")
        with c2:
            st.page_link("pages/2_📝_Register.py", label="Register", icon="📝")

st.divider()

# PHASE 3B: surfaced once (pop, not get) if find_or_create_google_user()
# failed on the linking rerun above — e.g. a transient database hiccup.
# st.user (Google's own session) is still signed in at this point, so
# the visitor can just retry without re-doing Google's consent screen.
google_link_error = st.session_state.pop("_google_link_error", None)
if google_link_error:
    st.error(f"Google sign-in succeeded, but we couldn't finish signing you in to EcoVision AI: {google_link_error}")

# ---------------------------------------------------------------
# HERO
# ---------------------------------------------------------------
st.markdown(
    """
    <div class="eco-hero">
        <div class="eco-float" style="font-size:3rem;">🌍♻️🌱</div>
        <h1>Smart Waste Management & Recycling in Indian Cities</h1>
        <p>An AI-powered Smart City platform that empowers citizens and municipal corporations
        to report waste, improve recycling, monitor cleanliness, and build sustainable
        communities using Artificial Intelligence.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

hc1, hc2, hc3, hc4 = st.columns(4)
with hc1:
    get_started_clicked = st.button(
        "🚀 Get Started", use_container_width=True, type="primary", key="landing_get_started",
    )
with hc2:
    st.page_link("pages/12_📈_Dashboard_Generator.py", label="📊 View Dashboard Demo", use_container_width=True)
with hc3:
    st.page_link("pages/9_🤖_Prakriti_AI_Connect.py", label="🌿 Talk to Prakriti AI", use_container_width=True)
with hc4:
    if st.button("▶ Explore Features", use_container_width=True):
        st.session_state["_scroll_features"] = True

# PHASE 3A: "Get Started" now opens the auth-choice popup above instead
# of switching straight to Register — see that dialog's own docstring
# for exactly where each choice leads. Checking the flag immediately
# after setting it (same run, no st.rerun() needed) matches how
# st.dialog is meant to be invoked.
if get_started_clicked:
    st.session_state["show_auth_choice"] = True
if st.session_state["show_auth_choice"]:
    _render_auth_choice_dialog()

st.markdown("---")

# ---------------------------------------------------------------
# FEATURES
# ---------------------------------------------------------------
st.markdown('<div class="eco-section-title">🌱 Platform Features</div>', unsafe_allow_html=True)
st.markdown('<div class="eco-section-sub">Everything a Smart City needs for sustainable waste management, in one platform.</div>', unsafe_allow_html=True)

features = [
    ("📢", "AI Waste Reporting", "Report waste issues in seconds with photo, location & AI-assisted description."),
    ("🤖", "AI Waste Classification", "Upload a photo — AI identifies plastic, organic, e-waste and more instantly."),
    ("♻️", "Recycling Guide", "Category-wise disposal & recycling guidance tailored for Indian households."),
    ("📍", "Complaint Tracking", "Track every complaint from submission to resolution in real time."),
    ("🌿", "Prakriti AI Connect", "24×7 bilingual AI sustainability assistant, on every page."),
    ("📊", "Dashboard Generator", "Upload any CSV/Excel and auto-generate KPI cards, charts & AI insights."),
    ("📈", "Smart Analytics", "Ward-wise, category-wise and time-series analytics for officers & admins."),
    ("🏆", "Green Rewards", "Earn points for responsible reporting and climb the city leaderboard."),
    ("📄", "AI Reports", "Generate citizen, officer and municipality reports in PDF/Excel."),
    ("🗺️", "Recycling Centre Locator", "Find the nearest authorized recycling & e-waste centres."),
    ("🌍", "Carbon Calculator", "Estimate your personal carbon footprint and get reduction tips."),
    ("🧑‍💼", "Officer Dashboard", "Complaint management, worker assignment & performance analytics."),
]

for row_start in range(0, len(features), 4):
    cols = st.columns(4)
    for col, (icon, title, desc) in zip(cols, features[row_start:row_start + 4]):
        with col:
            st.markdown(
                f"""<div class="eco-card">
                        <div style="font-size:2rem;">{icon}</div>
                        <div style="font-weight:700;margin:0.3rem 0;">{title}</div>
                        <div style="color:#94a3b8;font-size:0.88rem;">{desc}</div>
                    </div>""",
                unsafe_allow_html=True,
            )

# ---------------------------------------------------------------
# WHY CHOOSE US
# ---------------------------------------------------------------
st.markdown('<div class="eco-section-title">💡 Why Choose Our Platform</div>', unsafe_allow_html=True)
why = ["AI Powered", "Fast Complaint Resolution", "Interactive Dashboards", "Smart Analytics",
       "Citizen Engagement", "Smart City Ready", "Secure", "Scalable", "Cloud Hosted"]
cols = st.columns(3)
for i, w in enumerate(why):
    with cols[i % 3]:
        st.markdown(f'<span class="eco-pill">✔ {w}</span>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ---------------------------------------------------------------
# SDG SECTION
# ---------------------------------------------------------------
st.markdown('<div class="eco-section-title">🌎 Supporting the UN Sustainable Development Goals</div>', unsafe_allow_html=True)
sdg1, sdg2, sdg3 = st.columns(3)
with sdg1:
    st.markdown('<div class="eco-card" style="border-left:4px solid #FD9D24;"><h3>🏙️ SDG 11</h3><b>Sustainable Cities & Communities</b><p style="color:#94a3b8;">Cleaner, more resilient urban neighborhoods through smart complaint resolution.</p></div>', unsafe_allow_html=True)
with sdg2:
    st.markdown('<div class="eco-card" style="border-left:4px solid #BF8B2E;"><h3>♻️ SDG 12</h3><b>Responsible Consumption & Production</b><p style="color:#94a3b8;">Better segregation, recycling and reduced landfill burden.</p></div>', unsafe_allow_html=True)
with sdg3:
    st.markdown('<div class="eco-card" style="border-left:4px solid #3F7E44;"><h3>🌡️ SDG 13</h3><b>Climate Action</b><p style="color:#94a3b8;">Carbon tracking and awareness to reduce each citizen\'s footprint.</p></div>', unsafe_allow_html=True)

# ---------------------------------------------------------------
# STATISTICS
# ---------------------------------------------------------------
st.markdown('<div class="eco-section-title">📊 Platform Impact</div>', unsafe_allow_html=True)
stats = [("10,000+", "Complaints Managed"), ("95%", "AI Classification Accuracy"),
         ("50+", "Recycling Centres"), ("100%", "Cloud Powered"),
         ("24×7", "AI Assistant"), ("10×", "Faster Analytics")]
cols = st.columns(6)
for col, (num, label) in zip(cols, stats):
    with col:
        st.markdown(f'<div class="eco-stat"><div class="num">{num}</div><div class="label">{label}</div></div>', unsafe_allow_html=True)

# ---------------------------------------------------------------
# PRAKRITI AI PREVIEW
# ---------------------------------------------------------------
st.markdown('<div class="eco-section-title">🤖 Meet Prakriti AI Connect</div>', unsafe_allow_html=True)
p1, p2 = st.columns([1, 2])
with p1:
    st.markdown('<div style="font-size:5rem;text-align:center;" class="eco-float">🌿🤖</div>', unsafe_allow_html=True)
with p2:
    st.markdown(
        """<div class="eco-card">
        <div class="chat-bubble-user">🧑 How should I dispose of old batteries?</div>
        <div class="chat-bubble-ai">🌿 Old batteries are hazardous e-waste — never put them in your household bin.
        Drop them off at your nearest MCG e-waste collection centre, or hand them to an authorized
        e-waste collector. Want me to find the nearest centre for you?</div>
        </div>""",
        unsafe_allow_html=True,
    )
    st.page_link("pages/9_🤖_Prakriti_AI_Connect.py", label="💬 Start chatting with Prakriti AI Connect", icon="🌿")

# ---------------------------------------------------------------
# GREEN IMPACT (animated-style counters)
# ---------------------------------------------------------------
st.markdown('<div class="eco-section-title">🌿 Green Impact</div>', unsafe_allow_html=True)
impact = [("18.2 tons", "Plastic Waste Reduced"), ("3,400+", "Trees Saved (Est.)"),
          ("12,500+", "Citizens Registered"), ("9,800+", "Complaints Resolved"),
          ("68%", "Recycling Rate"), ("410 tons", "Carbon Reduction (Est.)")]
cols = st.columns(3)
for i, (num, label) in enumerate(impact):
    with cols[i % 3]:
        st.markdown(f'<div class="eco-stat"><div class="num">{num}</div><div class="label">{label}</div></div>', unsafe_allow_html=True)

# ---------------------------------------------------------------
# TESTIMONIALS
# ---------------------------------------------------------------
st.markdown('<div class="eco-section-title">⭐ What People Say</div>', unsafe_allow_html=True)
testimonials = [
    ("👩", "Priya Sharma", "Citizen, Sector 45", "I reported an overflowing bin and it was cleared within a day. The AI chatbot even told me how to compost my kitchen waste!"),
    ("👮", "R. Kumar", "MCG Sanitation Officer", "The dashboard makes it so much easier to prioritize high-risk complaints like biomedical waste across wards."),
    ("🧑‍🤝‍🧑", "Green Earth NGO", "Volunteer Partner", "The awareness generator helps us create campaign material for schools in minutes."),
]
cols = st.columns(3)
for col, (avatar, name, role, quote) in zip(cols, testimonials):
    with col:
        st.markdown(
            f"""<div class="eco-card">
                <div style="font-size:2rem;">{avatar}</div>
                <p style="color:#cbd5e1;font-style:italic;">"{quote}"</p>
                <b>{name}</b><br><span style="color:#94a3b8;font-size:0.85rem;">{role}</span>
            </div>""",
            unsafe_allow_html=True,
        )

# ---------------------------------------------------------------
# FAQ
# ---------------------------------------------------------------
st.markdown('<div class="eco-section-title">❓ Frequently Asked Questions</div>', unsafe_allow_html=True)
faqs = [
    ("How do I report waste?", "Register or log in as a citizen, go to 'Report Waste', upload a photo and location — our AI will classify it and generate a description automatically."),
    ("How does AI classify waste?", "We use a vision-capable AI model via OpenRouter to analyze your photo and predict the waste category with a confidence score."),
    ("Is my location secure?", "Location data is only used to route your complaint to the correct ward officer and is never shared publicly."),
    ("How does Prakriti AI Connect work?", "It's a bilingual (English/Hindi) AI chatbot available on every page to answer sustainability and waste-related questions."),
    ("Can I download reports?", "Yes — citizens, officers and admins can export PDF, Excel, CSV and HTML reports from their dashboards."),
]
for q, a in faqs:
    with st.expander(q):
        st.write(a)

# ---------------------------------------------------------------
# CONTACT + FOOTER
# ---------------------------------------------------------------
st.markdown('<div class="eco-section-title">📞 Contact Us</div>', unsafe_allow_html=True)
cc1, cc2, cc3 = st.columns(3)
with cc1:
    st.markdown(f'<div class="eco-card">📧 <b>Email</b><br>{settings.SUPPORT_EMAIL}</div>', unsafe_allow_html=True)
with cc2:
    st.markdown(f'<div class="eco-card">📱 <b>Phone</b><br>{settings.SUPPORT_PHONE}</div>', unsafe_allow_html=True)
with cc3:
    st.markdown(f'<div class="eco-card">🏢 <b>Office</b><br>{settings.MUNICIPALITY_NAME}</div>', unsafe_allow_html=True)

st.markdown(
    f"""
    <div class="eco-footer">
        🌿 <b>EcoVision AI</b> — Designed with ❤️ for Smart Sustainable Cities<br>
        Powered by Python · Streamlit · OpenRouter AI<br>
        © 2026 EcoVision AI. All rights reserved. ·
        <a href="#" style="color:#64748b;">Privacy Policy</a> ·
        <a href="#" style="color:#64748b;">Terms</a>
    </div>
    """,
    unsafe_allow_html=True,
)
