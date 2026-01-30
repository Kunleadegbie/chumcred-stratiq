# ==================================================
# pages/Register.py — User Registration (Pending)
# ==================================================

import streamlit as st

from services.auth import hash_password
from db.repository import create_user
from components.styling import apply_talentiq_sidebar_style


# ==================================================
# PAGE CONFIG (MUST BE FIRST)
# ==================================================

st.set_page_config(page_title="Register", layout="centered")


# ==================================================
# HIDE STREAMLIT DEFAULT UI
# ==================================================

apply_talentiq_sidebar_style()


# ==================================================
# UI
# ==================================================

st.title("📝 Create Account")

st.info(
    "After registration, your account must be approved by an administrator "
    "before you can log in."
)


st.image("assets/logo.png", width=120)

# ==================================================
# FORM
# ==================================================

with st.form("register_form"):

    full_name = st.text_input("Full Name")
    email = st.text_input("Email Address")
    password = st.text_input("Password", type="password")
    confirm = st.text_input("Confirm Password", type="password")

    submit = st.form_submit_button("Register")


# ==================================================
# SUBMIT
# ==================================================

if submit:

    if not full_name or not email or not password:

        st.error("All fields are required.")
        st.stop()


    if password != confirm:

        st.error("Passwords do not match.")
        st.stop()


    try:

        create_user(
            email=email.strip().lower(),
            name=full_name.strip(),
            password_hash=hash_password(password),
            role="Pending",
            is_active=0
        )


        st.success("✅ Registration successful.")

        st.info("Please wait for admin approval.")

        st.page_link("pages/Login.py", label="Go to Login")


    except Exception:

        st.error("Email already exists.")
