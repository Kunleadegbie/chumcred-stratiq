# pages/Login.py
import streamlit as st
from services.auth import authenticate

from components.styling import apply_talentiq_sidebar_style
from components.footer import render_footer


st.set_page_config(page_title="Login", layout="centered")

apply_talentiq_sidebar_style()

st.title("🔐 Login")

email = st.text_input("Email", placeholder="you@company.com")
password = st.text_input("Password", type="password")

if st.button("Login"):

    result = authenticate(email, password)

    if result is None:
        st.error("❌ Invalid email or password.")
        st.stop()

    if result == "PENDING":
        st.warning("⏳ Account pending approval. Please wait for admin.")
        st.stop()

    # success
    st.session_state["user"] = result
    st.success("✅ Login successful.")
    st.switch_page("pages/1_Home.py")

render_footer()
