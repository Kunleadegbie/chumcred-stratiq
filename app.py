import streamlit as st

# ==========================================================
# AUTO-BOOTSTRAP ADMIN (RUNS ON FIRST DEPLOY)
# ==========================================================

from db.repository import get_user_by_email, create_user
from services.auth import hash_password


def bootstrap_admin():

    admin_email = "chumcred@gmail.com"

    existing = get_user_by_email(admin_email)

    if not existing:

        create_user(
            email=admin_email,
            name="System Administrator",
            password_hash=hash_password("admin123"),
            role="Admin",
            is_active=1
        )

        print("Production admin account created.")


bootstrap_admin()

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

try:
    from components.sidebar import render_sidebar
    from components.styling import apply_talentiq_sidebar_style

    render_sidebar()
    apply_talentiq_sidebar_style()

except Exception as e:
    st.warning("Navigation system not loaded properly.")
    print("Sidebar load error:", e)

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
