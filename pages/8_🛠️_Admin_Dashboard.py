import streamlit as st
import pandas as pd
import plotly.express as px
from database.db import fetch_all, execute, fetch_one
from backend import analytics
from backend.auth import register_user
from utils.helpers import load_css, require_login

st.set_page_config(page_title="Admin Dashboard | EcoVision AI", page_icon="🛠️", layout="wide")
require_login(allowed_roles=["admin"])
load_css()

st.markdown('<div class="eco-hero"><h1>🛠️ Admin Control Center</h1><p>Manage users, officers, categories, and system-wide analytics.</p></div>', unsafe_allow_html=True)

kpis = analytics.kpi_summary()
k1, k2, k3, k4 = st.columns(4)
for col, (val, label) in zip([k1, k2, k3, k4],
    [(kpis["citizens"], "Registered Citizens"), (kpis["total_complaints"], "Total Complaints"),
     (f'{kpis["resolution_rate"]}%', "Resolution Rate"), (kpis["high_priority_open"], "High Priority Open")]):
    with col:
        st.markdown(f'<div class="eco-stat"><div class="num">{val}</div><div class="label">{label}</div></div>', unsafe_allow_html=True)

tab_users, tab_officers, tab_complaints, tab_categories, tab_analytics, tab_settings = st.tabs(
    ["👥 Users", "🧑‍💼 Officers", "📋 Complaints", "🗂️ Categories", "📊 Analytics", "⚙️ Settings"]
)

with tab_users:
    st.subheader("All Citizens")
    citizens = fetch_all("SELECT id, full_name, email, phone, ward, reward_points, is_active, created_at FROM users WHERE role='citizen'")
    if citizens:
        df = pd.DataFrame(citizens)
        st.dataframe(df, use_container_width=True)
        uid = st.number_input("User ID to toggle active status", min_value=0, step=1)
        if st.button("Toggle Active/Inactive"):
            u = fetch_one("SELECT is_active FROM users WHERE id=?", (uid,))
            if u:
                # PHASE 2B: unchanged — users.is_active stays INTEGER (0/1)
                # in Postgres (see supabase/migrations/001_init_schema.sql),
                # so this toggle expression needs no translation.
                execute("UPDATE users SET is_active=? WHERE id=?", (0 if u["is_active"] else 1, uid))
                st.success("Status updated.")
                st.rerun()
            else:
                st.error("User not found.")
    else:
        st.info("No citizens registered yet.")

with tab_officers:
    st.subheader("Officers")
    officers = fetch_all("SELECT id, full_name, email, phone, ward, created_at FROM users WHERE role='officer'")
    if officers:
        st.dataframe(pd.DataFrame(officers), use_container_width=True)
    else:
        st.info('No officers found. Click "Add Officer" to create the first officer.')

    st.markdown("**Add New Officer**")
    with st.form("add_officer"):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Full Name")
            email = st.text_input("Email")
        with c2:
            phone = st.text_input("Phone")
            ward = st.text_input("Assigned Ward")
        password = st.text_input("Temporary Password", type="password", value="Officer@123")
        submit = st.form_submit_button("Add Officer", type="primary")
    if submit:
        ok, result = register_user(name, email, phone, password, ward=ward, role="officer",
                                    security_question="What is your favorite city?", security_answer="reset")
        if ok:
            st.success(f"Officer '{name}' added successfully.")
            st.rerun()
        else:
            st.error(result)

with tab_complaints:
    st.subheader("All Complaints (System-wide)")
    complaints = fetch_all(
        "SELECT c.id, c.category, c.status, c.priority, c.ward, u.full_name as citizen, c.created_at "
        "FROM complaints c JOIN users u ON u.id=c.user_id ORDER BY c.created_at DESC LIMIT 200"
    )
    if complaints:
        st.dataframe(pd.DataFrame(complaints), use_container_width=True)
    else:
        st.info("No complaints have been submitted yet.")

with tab_categories:
    st.subheader("Waste Categories")
    categories = fetch_all("SELECT * FROM categories")
    st.dataframe(pd.DataFrame(categories)[["id", "name", "description", "is_active"]], use_container_width=True)

    with st.form("add_category"):
        c1, c2 = st.columns(2)
        with c1:
            new_name = st.text_input("Category Name")
        with c2:
            new_icon = st.text_input("Icon (emoji)")
        new_desc = st.text_area("Description")
        new_guide = st.text_area("Disposal Guide")
        add_submit = st.form_submit_button("Add Category")
    if add_submit and new_name:
        execute("INSERT OR IGNORE INTO categories (name, description, icon, disposal_guide) VALUES (?,?,?,?)",
                (new_name, new_desc, new_icon, new_guide))
        st.success(f"Category '{new_name}' added.")
        st.rerun()

with tab_analytics:
    cat_data = analytics.complaints_by_category()
    monthly = analytics.complaints_monthly_trend()

    if not cat_data and not monthly:
        st.info("📊 No analytics available yet.\n\nAdd users and complaints to generate insights.")
    else:
        r1, r2 = st.columns(2)
        with r1:
            if cat_data:
                fig = px.bar(pd.DataFrame(cat_data), x="category", y="count", title="Complaints by Category", color="category")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No category data available yet.")
        with r2:
            if monthly:
                fig = px.line(pd.DataFrame(monthly), x="month", y="count", title="Monthly Complaint Trend", markers=True)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No monthly trend data available yet.")

with tab_settings:
    st.subheader("System Settings")
    from config import settings as cfg
    st.write(f"**Municipality:** {cfg.MUNICIPALITY_NAME}")
    st.write(f"**Support Email:** {cfg.SUPPORT_EMAIL}")
    st.write(f"**AI Configured:** {'✅ Yes' if cfg.is_ai_configured() else '❌ No — add OPENROUTER_API_KEY to .env'}")
    st.write(f"**Database Path:** `{cfg.DATABASE_PATH}`")
    st.caption("Edit these values in your `.env` file — never hardcode secrets in source code.")
