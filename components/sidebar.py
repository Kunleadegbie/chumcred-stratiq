# components/sidebar.py

import os
import streamlit as st

from components.navigation import ROLE_PAGES


# ==========================================================
# SAFE NAVIGATION
# ==========================================================

def safe_page_link(label, path):

    if st.sidebar.button(label, use_container_width=True):
        st.switch_page(path)


# ==========================================================
# LOGOUT
# ==========================================================

def handle_logout():

    st.session_state.clear()
    st.switch_page("pages/Login.py")


# ==========================================================
# MAIN SIDEBAR
# ==========================================================

def render_sidebar():

    # ---------------- AUTH ----------------

    if "user" not in st.session_state:
        st.switch_page("pages/Login.py")
        st.stop()

    user = st.session_state["user"]

    role = user.get("role", "Analyst")
    name = user.get("full_name", "User")
    email = user.get("email", "")

    pages = ROLE_PAGES.get(role, ROLE_PAGES["Analyst"])


    # ---------------- LOGO ----------------

    BASE_DIR = os.path.dirname(os.path.dirname(__file__))

    logo_path = os.path.join(
        BASE_DIR,
        "assets",
        "logo.png"
    )


    # ---------------- UI ----------------

    with st.sidebar:

        if os.path.exists(logo_path):
            st.image(logo_path, width=160)

        st.divider()

        st.markdown("## 📊 Chumcred StratIQ")
        st.caption("AI Business & Financial Intelligence")

        st.divider()

        # Navigation
        for label, path in pages:
            safe_page_link(label, path)

        st.divider()

        # User Info
        st.markdown(f"**👤 {name}**")
        st.caption(email)
        st.caption(f"Role: {role}")

        st.divider()

        # Logout
        if st.button("🚪 Logout", use_container_width=True):
            handle_logout()
