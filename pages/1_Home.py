
import streamlit as st

from core.roles import ROLE_PAGES
from db.repository import get_reviews


# ---------------- Auth Guard ----------------
if "user" not in st.session_state:
    st.switch_page("pages/Login.py")
    st.stop()


# ---------------- Role Guard ----------------
role = st.session_state["user"]["role"]

page_name = "1_Home"

if page_name not in ROLE_PAGES.get(role, []):
    st.error("⛔ Access denied.")
    st.stop()

from components.styling import apply_talentiq_sidebar_style
apply_talentiq_sidebar_style()

# ---------------- Sidebar ----------------
from components.sidebar import render_sidebar
render_sidebar()


# ---------------- Main ----------------
st.title("🏠 Home")

reviews = get_reviews()

if not reviews:
    st.info("No reviews yet. Create one to begin.")
else:
    st.subheader("Existing Reviews")

    for r in reviews:
        st.write(f"#{r[0]} | {r[1]} ({r[2]}) | {r[3]}")

st.divider()
st.write("➡ Go to **New Review** to create a new assessment.")


# other imports
from components.footer import render_footer

# page code ...

render_footer()

