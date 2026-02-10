import streamlit as st

from db.repository import get_user_by_email, create_user
from services.auth import hash_password


# ==========================================================
# AUTO BOOTSTRAP ADMIN
# ==========================================================

def bootstrap_admin():
    """
    Ensures a working Admin account exists and is ACTIVE.
    Fixes Railway issues where password was stored un-hashed,
    causing 'Invalid email or password'.
    """
    from services.auth import hash_password
    from db.repository import (
        get_user_by_email,
        create_user,
        update_user_role,
        activate_user,
        get_conn,
    )

    admin_email = "chumcred@gmail.com"
    admin_pass = "admin123"
    admin_name = "Chumcred Admin"

    existing = get_user_by_email(admin_email)

    if not existing:
        # create with HASHED password
        create_user(
            email=admin_email,
            full_name=admin_name,
            password_hash=hash_password(admin_pass),
            role="Admin",
            is_active=1
        )
        return

    # Ensure role is Admin (use user_id, not email)
    try:
        if (existing["role"] or "").strip().lower() != "admin":
            update_user_role(existing["id"], "Admin")
    except Exception:
        pass

    # Ensure account is active
    try:
        if int(existing["is_active"] or 0) != 1:
            activate_user(existing["id"])
    except Exception:
        pass

    # Ensure password is HASHED in DB (fix previously-created bad row)
    try:
        desired = hash_password(admin_pass)
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET password_hash=? WHERE email=?",
            (desired, admin_email)
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


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
