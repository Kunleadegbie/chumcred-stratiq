
# ==========================================================
# components/sidebar.py — ROLE-BASED NAVIGATION (STABLE)
# ==========================================================

import os
import streamlit as st


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


# ==========================================================
# MAIN SIDEBAR
# ==========================================================

def render_sidebar():

    BASE_DIR = os.path.dirname(os.path.dirname(__file__))

    logo_path = os.path.join(
        BASE_DIR,
        "assets",
        "logo.png"
    )

    with st.sidebar:

        # Show Logo
        if os.path.exists(logo_path):
            st.image(logo_path, width=160)

        st.markdown("---")

   

    # --------------------------------
    # AUTH CHECK
    # --------------------------------

    if "user" not in st.session_state:
        st.switch_page("pages/Login.py")
        st.stop()


    user = st.session_state.get("user", {})

    role = user.get("role", "Analyst")  # Default: Analyst
    name = user.get("full_name", "User")
    email = user.get("email", "")


    # --------------------------------
    # GET ROLE MENU
    # --------------------------------

    pages = ROLE_PAGES.get(role, ROLE_PAGES["Analyst"])


    # --------------------------------
    # SIDEBAR UI
    # --------------------------------

    with st.sidebar:

        # ---------- Branding ----------

        st.markdown("## 📊 Company Diagnostic")
        st.caption("Business Health & Strategy Platform")

        st.divider()


        # ---------- Navigation ----------

        for label, path in pages:

            safe_page_link(path, label)


        st.divider()


        # ---------- User Info ----------

        st.markdown(f"**👤 {name}**")
        st.caption(email)
        st.caption(f"Role: {role}")


        st.divider()


        # ---------- Logout ----------

        if st.button("🚪 Logout", use_container_width=True):
            handle_logout()


# ==========================================================
# LOGOUT
# ==========================================================

def handle_logout():

    st.session_state.clear()

    st.switch_page("pages/Login.py")
