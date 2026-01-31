import streamlit as st


# ==========================================================
# PAGE CONFIG (MUST BE FIRST)
# ==========================================================

st.set_page_config(
    page_title="Chumcred StratIQ",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# ==========================================================
# AUTH CHECK
# ==========================================================

if "user" not in st.session_state:
    st.switch_page("pages/Login.py")
    st.stop()


# ==========================================================
# SIDEBAR + STYLING
# ==========================================================

from components.sidebar import render_sidebar
from components.styling import apply_talentiq_sidebar_style

render_sidebar()
apply_talentiq_sidebar_style()


# ==========================================================
# MAIN DASHBOARD
# ==========================================================

user = st.session_state["user"]

st.title("📊 Chumcred StratIQ")

st.caption(
    f"Welcome, {user.get('full_name','User')} "
    f"({user.get('role','')})"
)

st.markdown(
    """
    **AI-Powered Business & Financial Intelligence Platform**

    Use the navigation menu to:
    - Create and analyze reviews
    - Enter financial and KPI data
    - Generate board reports
    - Access AI advisory
    """
)

st.markdown("---")

st.info(
    "Tip: Complete a review and financial analysis first "
    "to unlock full StratIQ insights."
)
