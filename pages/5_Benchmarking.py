import streamlit as st
import pandas as pd

from core.roles import ROLE_PAGES
from db.repository import get_reviews, get_scores, get_review_by_id
from core.benchmarking import compare_to_benchmark


# ---------------- Auth Guard ----------------
if "user" not in st.session_state:
    st.switch_page("pages/Login.py")
    st.stop()


# ---------------- Role Guard ----------------
role = st.session_state["user"]["role"]

page_name = "5_Benchmarking"

if page_name not in ROLE_PAGES.get(role, []):
    st.error("⛔ Access denied.")
    st.stop()

from components.styling import apply_talentiq_sidebar_style
apply_talentiq_sidebar_style()

# ---------------- Sidebar ----------------
from components.sidebar import render_sidebar
render_sidebar()


# ---------------- Main ----------------
st.title("📊 Industry Benchmarking")

reviews = get_reviews()

if not reviews:
    st.stop()


review_map = {
    f"{r[1]} (#{r[0]})": r[0]
    for r in reviews
}

selected = st.selectbox(
    "Select Review",
    list(review_map.keys())
)

review_id = review_map[selected]

st.session_state["active_review"] = review_id


review = get_review_by_id(review_id)

industry = review[2]


scores = get_scores(review_id)

if not scores:
    st.warning("⚠️ No scores found yet.")
    st.info("Please go to **Scoring Dashboard** and compute scores first.")
    st.stop()



results = compare_to_benchmark(scores, industry)

if not results:
    st.info("No benchmarks.")
    st.stop()


df = pd.DataFrame(results)

st.dataframe(df, use_container_width=True)

# other imports
from components.footer import render_footer

# page code ...

render_footer()

