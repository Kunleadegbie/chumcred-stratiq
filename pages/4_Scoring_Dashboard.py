
import streamlit as st
import pandas as pd

from core.roles import ROLE_PAGES
from db.repository import (
    get_reviews,
    get_kpi_inputs,
    save_scores,
    get_scores
)

from core.billing_engine import can_export
from db.repository import increment_exports

from core.scoring_engine import compute_scores
from core.pdf_engine import export_report_to_pdf

from components.styling import apply_talentiq_sidebar_style
from components.sidebar import render_sidebar


# ==================================================
# AUTH GUARD
# ==================================================

if "user" not in st.session_state:
    st.switch_page("pages/Login.py")
    st.stop()


# ==================================================
# ROLE GUARD
# ==================================================

role = st.session_state["user"]["role"]

page_name = "4_Scoring_Dashboard"

if page_name not in ROLE_PAGES.get(role, []):
    st.error("⛔ Access denied.")
    st.stop()


# ==================================================
# UI STYLING
# ==================================================

apply_talentiq_sidebar_style()
render_sidebar()


# ==================================================
# MAIN PAGE
# ==================================================

st.title("📈 Scoring Dashboard")


# ==================================================
# LOAD REVIEWS
# ==================================================

reviews = get_reviews()

if not reviews:
    st.warning("No reviews found.")
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


# ==================================================
# KPI INPUT CHECK
# ==================================================

inputs = get_kpi_inputs(review_id)

if not inputs:
    st.warning("No KPI data found. Please enter KPI values first.")
    st.stop()


# ==================================================
# SCORE COMPUTATION
# ==================================================

st.subheader("Scoring Engine")

if st.button("⚙️ Compute Scores"):

    with st.spinner("Computing scores..."):

        results, pillars, bhi = compute_scores(inputs)

        save_scores(review_id, results)

    st.success("✅ Scores computed successfully.")


# ==================================================
# LOAD SCORES
# ==================================================

scores = get_scores(review_id)

if not scores:
    st.info("Click **Compute Scores** to generate results.")
    st.stop()


# ==================================================
# NORMALIZE SCORE DATA
# ==================================================
# Supports dict and tuple formats safely

rows = []

for item in scores:

    # Dict format
    if isinstance(item, dict):

        kpi = item.get("kpi")
        value = item.get("raw_value")
        score = item.get("score")
        pillar = item.get("pillar")

    # Tuple format
    elif isinstance(item, (list, tuple)) and len(item) >= 4:

        kpi = item[0]
        value = item[1]
        score = item[2]
        pillar = item[3]

    else:
        continue


    try:
        score = float(score)
    except:
        score = 0


    rows.append([kpi, value, score, pillar])


df = pd.DataFrame(
    rows,
    columns=["KPI", "Value", "Score", "Pillar"]
)


# ==================================================
# KPI TABLE
# ==================================================

st.subheader("📋 KPI Scores")

st.dataframe(df, use_container_width=True)


# ==================================================
# PILLAR SUMMARY
# ==================================================

st.subheader("📊 Pillar Averages")

pillar_df = (
    df.groupby("Pillar")["Score"]
    .mean()
    .reset_index()
    .round(2)
)

st.dataframe(pillar_df, use_container_width=True)


# ==================================================
# BUSINESS HEALTH INDEX
# ==================================================

bhi = round(pillar_df["Score"].mean(), 2)

st.metric("Business Health Index (BHI)", bhi)


# ==================================================
# PDF EXPORT (ADMIN / CEO ONLY)
# ==================================================

st.divider()
st.subheader("📄 Board Report Export")


# Get logged-in user info
user = st.session_state.get("user")

if not user:
    st.switch_page("pages/Login.py")
    st.stop()

user_id = user["id"]
user_role = user["role"]
st.write("DEBUG ROLE:", user_role)


is_admin = user_role.strip().lower() in ("admin", "ceo")
has_export = can_export(user_id)

if is_admin and has_export:

    brand_mode = st.radio(
        "Report Branding",
        ["branded", "white_label"],
        horizontal=True
    )


    if st.button("📥 Generate PDF Report"):

        with st.spinner("Generating report..."):

            path = export_report_to_pdf(
                review_id,
                brand_mode=brand_mode
            )

        st.success("✅ Report generated successfully.")

        increment_exports(user_id)

        with open(path, "rb") as f:

            st.download_button(
                "⬇️ Download Report",
                data=f,
                file_name=path.split("\\")[-1],
                mime="application/pdf"
            )


else:

    st.info("Only Admins and CEOs can export official reports.")

# other imports
from components.footer import render_footer

# page code ...

render_footer()

