# ==================================================
# pages/Login.py — Secure Login with Approval Check
# ==================================================

import streamlit as st

from services.auth import authenticate
from components.styling import apply_talentiq_sidebar_style


# ==================================================
# UI STYLING
# ==================================================

apply_talentiq_sidebar_style()


# ==================================================
# PAGE HEADER
# ==================================================

st.title("🔐 Chumcred StratIQ (Login)")

st.caption("Secure access to the diagnostic platform")


st.image("assets/logo.png", width=120)

# ==================================================
# REDIRECT IF LOGGED IN
# ==================================================

if st.session_state.get("user"):
    st.switch_page("app.py")
    st.stop()


# ==================================================
# LOGIN FORM
# ==================================================

with st.form("login_form"):

    email = st.text_input("Email")

    password = st.text_input("Password", type="password")

    submitted = st.form_submit_button("Login")


# ==================================================
# HANDLE LOGIN
# ==================================================

if submitted:

    try:

        user = authenticate(email, password)

        if not user:

            st.error("❌ Invalid email or password.")
            st.stop()


        # Success
        st.session_state["user"] = user

        st.success("✅ Login successful.")

        st.switch_page("app.py")


    except ValueError as e:

        # Pending approval or other auth errors
        st.warning(str(e))
        st.stop()


st.divider()

st.caption("Don't have an account?")

st.page_link("pages/Register.py", label="📝 Create an account")

