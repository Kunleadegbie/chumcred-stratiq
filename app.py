import streamlit as st

from db.repository import get_user_by_email, create_user
from services.auth import hash_password


# ==========================================================
# AUTO BOOTSTRAP ADMIN
# ==========================================================

def bootstrap_admin():

    admin_email = "chumcred@gmail.com"

    user = get_user_by_email(admin_email)

    if not user:

        create_user(
            email=admin_email,
            name="System Administrator",
            password_hash=hash_password("admin123"),
            role="Admin",
            is_active=1
        )

    else:

        # Force role correction
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
            UPDATE users
            SET role='Admin', is_active=1
            WHERE email=?
        """, (admin_email,))

        conn.commit()
        conn.close()


# ==========================================================
# PAGE CONFIG (MUST BE FIRST)
# ==========================================================

st.set_page_config(
    page_title="Chumcred StratIQ",
    layout="wide",
    initial_sidebar_state="expanded"
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
