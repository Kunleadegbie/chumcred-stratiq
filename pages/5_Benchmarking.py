# pages/5_Benchmarking.py
import streamlit as st
import pandas as pd

from core.roles import ROLE_PAGES
from db.repository import get_reviews, get_scores, get_review_by_id
from core.benchmarking import compare_to_benchmark

from components.styling import apply_talentiq_sidebar_style
from components.sidebar import render_sidebar
from components.footer import render_footer


def _norm(s):
    return str(s or "").strip().lower()


# ---------------- Auth Guard ----------------
if "user" not in st.session_state:
    st.switch_page("pages/Login.py")
    st.stop()

# ---------------- Role Guard ----------------
role = (st.session_state["user"].get("role") or "").strip()
page_name = "5_Benchmarking"

allowed = ROLE_PAGES.get(role, [])
if allowed and page_name not in allowed:
    # keep app usable like your other pages
    pass

apply_talentiq_sidebar_style()
render_sidebar()

st.title("📊 Industry Benchmarking")

reviews = get_reviews()
if not reviews:
    st.warning("No reviews found yet.")
    st.info("Start with: New Review → Data Input → Scoring")
    render_footer()
    st.stop()

review_map = {f"{r[1]} (#{r[0]})": r[0] for r in reviews}
selected = st.selectbox("Select Review", list(review_map.keys()))
review_id = review_map[selected]
st.session_state["active_review"] = review_id

review = get_review_by_id(review_id)
# Defensive: review might be tuple with industry at index 2, but could differ
industry = ""
try:
    industry = review[2]
except Exception:
    industry = ""

industry_norm = _norm(industry)

scores = get_scores(review_id)
if not scores:
    st.warning("⚠️ No scores found yet.")
    st.info("Please go to **Scoring Dashboard** and compute scores first.")
    render_footer()
    st.stop()

results = compare_to_benchmark(scores, industry)

if not results:
    st.info("No benchmarks available for this industry.")
    st.caption(f"Debug: industry from review = '{industry}' (normalized='{industry_norm}')")
    st.caption("If you believe this industry exists, confirm the benchmark store uses the same name/spelling.")
    render_footer()
    st.stop()

df = pd.DataFrame(results)
st.dataframe(df, use_container_width=True)

render_footer()
