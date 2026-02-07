import streamlit as st
import pandas as pd

from core.roles import ROLE_PAGES
from db.repository import get_reviews, get_scores, get_review_by_id
from core.benchmarking import compare_to_benchmark

from components.styling import apply_talentiq_sidebar_style
from components.sidebar import render_sidebar
from components.footer import render_footer


# ---------------- Auth Guard ----------------
if "user" not in st.session_state:
    st.switch_page("pages/Login.py")
    st.stop()


# ---------------- Role Guard (robust to ROLE_PAGES formats) ----------------
role = (st.session_state["user"].get("role") or "").strip()
page_name = "5_Benchmarking"

allowed = ROLE_PAGES.get(role, [])
allowed_names = set()
for item in allowed:
    if isinstance(item, str):
        allowed_names.add(item)
    elif isinstance(item, (list, tuple)) and item:
        allowed_names.add(str(item[0]))
        if len(item) > 1:
            allowed_names.add(str(item[1]))

if (page_name not in allowed_names) and (page_name not in allowed):
    st.error("⛔ Access denied.")
    st.stop()


# ---------------- UI Styling + Sidebar ----------------
apply_talentiq_sidebar_style()
render_sidebar()

st.title("📊 Industry Benchmarking")


# ---------------- Reviews ----------------
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


# ---------------- Industry ----------------
review = get_review_by_id(review_id)
industry = ""
try:
    # tuple-like (id, name, industry, ...)
    industry = (review[2] or "").strip() if review and len(review) > 2 else ""
except Exception:
    # dict-like
    try:
        industry = (review.get("industry") or "").strip() if isinstance(review, dict) else ""
    except Exception:
        industry = ""


# ---------------- Scores ----------------
scores = get_scores(review_id)
if not scores:
    st.warning("⚠️ No scores found yet.")
    st.info("Please go to **Scoring Dashboard** and compute scores first.")
    render_footer()
    st.stop()


# ---------------- Benchmark Compare ----------------
results = compare_to_benchmark(scores, industry)

if not results:
    st.info("No benchmarks available for this industry.")
    render_footer()
    st.stop()

df = pd.DataFrame(results)
st.dataframe(df, use_container_width=True)

render_footer()
