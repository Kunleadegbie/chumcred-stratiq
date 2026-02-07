import os
import math
import streamlit as st
import pandas as pd

from core.roles import ROLE_PAGES
from db.repository import (
    get_reviews,
    get_kpi_inputs,
    save_scores,
    get_scores,
    increment_exports,
)

from core.scoring_engine import compute_scores
from core.pdf_engine import export_report_to_pdf

from components.styling import apply_talentiq_sidebar_style
from components.sidebar import render_sidebar
from components.footer import render_footer


# ----------------------------------------------------------
# SAFE IMPORTS (billing_engine may not have record_export)
# ----------------------------------------------------------
try:
    from core.billing_engine import can_export, record_export  # type: ignore
except Exception:
    from core.billing_engine import can_export  # type: ignore

    def record_export(*args, **kwargs):  # noqa: D401
        """Fallback no-op if record_export does not exist."""
        return None


# ==================================================
# AUTH GUARD
# ==================================================
if "user" not in st.session_state:
    st.switch_page("pages/Login.py")
    st.stop()

user = st.session_state.get("user") or {}
role = (user.get("role") or "").strip()
role_lc = role.lower()

page_name = "4_Scoring_Dashboard"


# ==================================================
# ROLE GUARD (ROBUST LIKE DATA INPUT PAGE)
# ==================================================
allowed = ROLE_PAGES.get(role, [])
allowed_names = set()

for item in allowed:
    if isinstance(item, str):
        allowed_names.add(item)
    elif isinstance(item, (list, tuple)) and item:
        allowed_names.add(str(item[0]))
        allowed_names.add(str(item[1]))

if (page_name not in allowed_names) and (page_name not in allowed):
    st.error("⛔ Access denied.")
    st.stop()


# ==================================================
# UI
# ==================================================
apply_talentiq_sidebar_style()
render_sidebar()

st.title("📈 Scoring Dashboard")


# ==================================================
# LOAD REVIEWS
# ==================================================
reviews = get_reviews()
if not reviews:
    st.warning("No reviews found.")
    render_footer()
    st.stop()

review_labels = [f"{r[1]} (#{r[0]})" for r in reviews]
review_map = {label: r[0] for label, r in zip(review_labels, reviews)}

selected = st.selectbox("Select Review", review_labels)
review_id = review_map[selected]
st.session_state["active_review"] = review_id


# ==================================================
# KPI INPUT CHECK
# ==================================================
inputs = get_kpi_inputs(review_id)  # expected dict(kpi_id -> value)
if not inputs:
    st.warning("No KPI data found. Please enter KPI values first.")
    render_footer()
    st.stop()


# ==================================================
# COMPUTE SCORES
# ==================================================
st.subheader("Scoring Engine")

if st.button("⚙️ Compute Scores"):
    with st.spinner("Computing scores..."):
        results, pillars, bhi = compute_scores(inputs)

        # Persist computed KPI-level scores
        save_scores(review_id, results)

        # Keep last computed values in session for display (optional)
        st.session_state["last_pillars"] = pillars
        st.session_state["last_bhi"] = bhi

    st.success("✅ Scores computed successfully.")
    st.rerun()


# ==================================================
# LOAD SCORES
# ==================================================
scores = get_scores(review_id)
if not scores:
    st.info("Click **Compute Scores** to generate results.")
    render_footer()
    st.stop()


# ==================================================
# NORMALIZE SCORE DATA (NO NaN)
# ==================================================
def _safe_float(x, default=0.0) -> float:
    try:
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return float(default)
        return v
    except Exception:
        return float(default)


rows = []
for item in scores:
    # Dict format
    if isinstance(item, dict):
        kpi = item.get("kpi") or item.get("kpi_id") or item.get("id")
        value = item.get("raw_value", item.get("value", 0))
        score = item.get("score", 0)
        pillar = item.get("pillar", "UNKNOWN")

    # Tuple/list format
    elif isinstance(item, (list, tuple)) and len(item) >= 4:
        kpi = item[0]
        value = item[1]
        score = item[2]
        pillar = item[3]
    else:
        continue

    score_f = _safe_float(score, 0.0)
    value_f = _safe_float(value, 0.0)

    rows.append([str(kpi), value_f, score_f, str(pillar or "UNKNOWN")])


df = pd.DataFrame(rows, columns=["KPI", "Value", "Score", "Pillar"])

# Ensure no NaN remains
df["Score"] = df["Score"].fillna(0.0)
df["Value"] = df["Value"].fillna(0.0)
df["Pillar"] = df["Pillar"].fillna("UNKNOWN")


# ==================================================
# KPI TABLE
# ==================================================
st.subheader("📋 KPI Scores")
st.dataframe(df, use_container_width=True)


# ==================================================
# PILLAR SUMMARY
# ==================================================
st.subheader("📊 Pillar Averages")

if df.empty:
    pillar_df = pd.DataFrame(columns=["Pillar", "Score"])
else:
    pillar_df = (
        df.groupby("Pillar", dropna=False)["Score"]
        .mean()
        .reset_index()
        .round(2)
    )

pillar_df["Score"] = pillar_df["Score"].fillna(0.0)
st.dataframe(pillar_df, use_container_width=True)


# ==================================================
# BUSINESS HEALTH INDEX
# ==================================================
# Prefer engine BHI if present + valid; else compute from pillar average safely
engine_bhi = st.session_state.get("last_bhi", None)
engine_bhi = _safe_float(engine_bhi, default=float("nan"))

if not math.isnan(engine_bhi):
    bhi_value = round(engine_bhi, 2)
else:
    if len(pillar_df) == 0:
        bhi_value = 0.0
    else:
        bhi_value = round(_safe_float(pillar_df["Score"].mean(), 0.0), 2)

st.metric("Business Health Index (BHI)", bhi_value)


# ==================================================
# PDF EXPORT (ADMIN / CEO ONLY)
# ==================================================
st.divider()
st.subheader("📄 Board Report Export")

user_id = user.get("id")
if user_id is None:
    st.switch_page("pages/Login.py")
    st.stop()

is_admin_ceo = role_lc in ("admin", "ceo")

# Debug line (keep if you want)
st.write("DEBUG ROLE:", role)

if not is_admin_ceo:
    st.info("Only Admins and CEOs can export official reports.")
    render_footer()
    st.stop()

has_export = bool(can_export(user_id))

if not has_export:
    st.warning("Export limit reached or export not enabled for this account.")
    render_footer()
    st.stop()

brand_mode = st.radio("Report Branding", ["branded", "white_label"], horizontal=True)

if st.button("📥 Generate PDF Report"):
    with st.spinner("Generating report..."):
        path = export_report_to_pdf(review_id, brand_mode=brand_mode)

    # Track export usage (both patterns supported)
    try:
        record_export(user_id, review_id)
    except Exception:
        pass

    try:
        increment_exports(user_id)
    except Exception:
        pass

    st.success("✅ Report generated successfully.")

    filename = os.path.basename(path) if path else "board_report.pdf"
    with open(path, "rb") as f:
        st.download_button(
            "⬇️ Download Report",
            data=f,
            file_name=filename,
            mime="application/pdf",
        )

render_footer()
