
# ==========================================================
# components/sidebar.py — ROLE-BASED NAVIGATION (STABLE)
# ==========================================================

import os
import streamlit as st

from components.navigation import ROLE_PAGES, safe_page_link



# ==========================================================
# UTILITIES
# ==========================================================

def _page_exists(path: str) -> bool:
    return os.path.exists(path)


def safe_page_link(path: str, label: str):
    """
    Render page link only if file exists
    """
    if _page_exists(path):
        try:
            st.page_link(path, label=label)
        except Exception:
            pass


# ==========================================================
# ROLE MENU DEFINITIONS
# ==========================================================

ROLE_PAGES = {

    # -------------------------
    # ADMIN
    # -------------------------
    "Admin": [

        ("🏠 Home", "pages/1_Home.py"),
        ("➕ New Review", "pages/2_New_Review.py"),
        ("📊 Financial Analyzer", "pages/11_Financial_Analyzer.py"),
        ("📝 Data Input", "pages/3_Data_Input.py"),
        ("📈 Scoring", "pages/4_Scoring_Dashboard.py"),
        ("📊 Benchmarking", "pages/5_Benchmarking.py"),
        ("🧭 SWOT", "pages/6_SWOT.py"),
        ("💡 Recommendations", "pages/7_Recommendations.py"),

        ("🧠 Advisor", "pages/9_Advisor.py"),
        ("💳 Subscription", "pages/10_Subscription.py"),


        ("⚙️ System Config", "pages/8_Admin_Config.py"),
    ],


    # -------------------------
    # CEO
    # -------------------------
    "CEO": [

        ("🏠 Home", "pages/1_Home.py"),
        ("📈 Scoring", "pages/4_Scoring_Dashboard.py"),
        ("📊 Benchmarking", "pages/5_Benchmarking.py"),
        ("🧭 SWOT", "pages/6_SWOT.py"),
        ("💡 Recommendations", "pages/7_Recommendations.py"),

        ("🧠 Advisor", "pages/9_Advisor.py"),
        ("💳 Subscription", "pages/10_Subscription.py"),

    ],


    # -------------------------
    # ANALYST
    # -------------------------
    "Analyst": [

        ("🏠 Home", "pages/1_Home.py"),
        ("➕ New Review", "pages/2_New_Review.py"),
        ("📊 Financial Analyzer", "pages/11_Financial_Analyzer.py"),
        ("📝 Data Input", "pages/3_Data_Input.py"),
        ("📈 Scoring", "pages/4_Scoring_Dashboard.py"),
        ("📊 Benchmarking", "pages/5_Benchmarking.py"),
        ("🧭 SWOT", "pages/6_SWOT.py"),
        ("💡 Recommendations", "pages/7_Recommendations.py"),
        ("💳 Subscription", "pages/10_Subscription.py"),

    ],
}


import streamlit as st
import os

# ==========================================================
# ROLE-BASED NAVIGATION
# ==========================================================

ROLE_PAGES = {

    "Admin": [
        ("🏠 Home", "pages/1_Home.py"),
        ("📝 New Review", "pages/2_New_Review.py"),
        ("📊 Data Input", "pages/3_Data_Input.py"),
        ("📈 Scoring", "pages/4_Scoring_Dashboard.py"),
        ("📊 Benchmarking", "pages/5_Benchmarking.py"),
        ("📌 SWOT", "pages/6_SWOT.py"),
        ("💡 Recommendations", "pages/7_Recommendations.py"),
        ("⚙️ Admin Config", "pages/8_Admin_Config.py"),
        ("🤖 Advisor", "pages/9_Advisor.py"),
        ("📑 Financial Analyzer", "pages/11_Financial_Analyzer.py"),
    ],

    "CEO": [
        ("🏠 Home", "pages/1_Home.py"),
        ("📈 Scoring", "pages/4_Scoring_Dashboard.py"),
        ("📊 Benchmarking", "pages/5_Benchmarking.py"),
        ("💡 Recommendations", "pages/7_Recommendations.py"),
        ("🤖 Advisor", "pages/9_Advisor.py"),
        ("📑 Financial Analyzer", "pages/11_Financial_Analyzer.py"),
    ],

    "Analyst": [
        ("🏠 Home", "pages/1_Home.py"),
        ("📝 New Review", "pages/2_New_Review.py"),
        ("📊 Data Input", "pages/3_Data_Input.py"),
        ("📈 Scoring", "pages/4_Scoring_Dashboard.py"),
        ("📑 Financial Analyzer", "pages/11_Financial_Analyzer.py"),
    ]
}


# ==========================================================
# SAFE PAGE LINK
# ==========================================================

def safe_page_link(path, label):

    if st.sidebar.button(label, use_container_width=True):
        st.switch_page(path)


# ==========================================================
# MAIN SIDEBAR
# ==========================================================

def render_sidebar():

    # --------------------------------
    # AUTH CHECK
    # --------------------------------

    if "user" not in st.session_state:
        st.switch_page("pages/Login.py")
        st.stop()

    user = st.session_state["user"]

    role = user.get("role", "Analyst")
    name = user.get("full_name", "User")
    email = user.get("email", "")

    pages = ROLE_PAGES.get(role, ROLE_PAGES["Analyst"])


    # --------------------------------
    # LOGO PATH
    # --------------------------------

    BASE_DIR = os.path.dirname(os.path.dirname(__file__))

    logo_path = os.path.join(
        BASE_DIR,
        "assets",
        "logo.png"
    )


    # --------------------------------
    # SIDEBAR UI
    # --------------------------------

    with st.sidebar:

        # Logo
        if os.path.exists(logo_path):
            st.image(logo_path, width=160)

        st.divider()

        # Branding
        st.markdown("## 📊 Chumcred StratIQ")
        st.caption("AI Business Intelligence Platform")

        st.divider()

        # Navigation
        for label, path in pages:
            safe_page_link(path, label)

        st.divider()

        # User Info
        st.markdown(f"**👤 {name}**")
        st.caption(email)
        st.caption(f"Role: {role}")

        st.divider()

        # Logout
        if st.button("🚪 Logout", use_container_width=True):
            handle_logout()


# ==========================================================
# LOGOUT
# ==========================================================

def handle_logout():

    st.session_state.clear()

    st.switch_page("pages/Login.py")
