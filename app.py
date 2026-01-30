import streamlit as st
from db.repository import init_db


st.set_page_config(
    page_title="Company Diagnostic Platform",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ---------------- Sidebar ----------------
from components.sidebar import render_sidebar
render_sidebar()

from components.styling import apply_talentiq_sidebar_style
apply_talentiq_sidebar_style()

if "db_init" not in st.session_state:
    init_db()
    st.session_state["db_init"] = True

if "user" not in st.session_state:
    st.switch_page("pages/Login.py")
    st.stop()

st.title("📊 Company Diagnostic Platform")
user = st.session_state["user"]
st.caption(f"Welcome, {user.get('name','User')} ({user.get('role','')})")
st.write("Use the sidebar navigation to proceed.")
