# ==========================================================
# pages/4_Scoring_Dashboard.py — Scoring Dashboard (FIXED)
# ==========================================================

from __future__ import annotations

import math
import streamlit as st

from core.roles import ROLE_PAGES
from core.kpi_registry import load_kpis
from db.repository import get_reviews, get_kpi_inputs, get_review_by_id

from components.styling import apply_talentiq_sidebar_style
from components.sidebar import render_sidebar
from components.footer import render_footer


# ---------------- Helpers ----------------
def _norm(s):
    return str(s or "").strip().lower()


def _to_float(x, default=0.0):
    try:
        v = float(x)
        if v != v:  # NaN
            return default
        return v
    except Exception:
        return default


def _score_value(value: float, cfg: dict) -> float:
    """
    cfg has scoring_rules like:
      {min: null/max: 0/score: 1} ...
    direction is informational here (your rules already encode it).
    """
    rules = cfg.get("scoring_rules") or []
    v = _to_float(value, 0.0)

    for r in rules:
        mn = r.get("min", None)
        mx = r.get("max", None)
        score = r.get("score", None)
        if score is None:
            continue

        ok_min = True if mn is None else (v >= float(mn))
        ok_max = True if mx is None else (v <= float(mx))
        if ok_min and ok_max:
            return float(score)

    # If it doesn't match any rule, return 0 (never NaN)
    return 0.0


def _mean(nums):
    nums = [n for n in nums if isinstance(n, (int, float)) and not math.isnan(n)]
    if not nums:
        return 0.0
    return sum(nums) / len(nums)


# ---------------- Auth Guard ----------------
if "user" not in st.session_state:
    st.switch_page("pages/Login.py")
    st.stop()

# ---------------- Role Guard (robust to ROLE_PAGES formats) ----------------
role_raw = (st.session_state["user"].get("role") or "").strip()
role = _norm(role_raw)
page_name = "4_Scoring_Dashboard"

allowed = ROLE_PAGES.get(role_raw, ROLE_PAGES.get(role, [])) or []
allowed_names = set()
for item in allowed:
    if isinstance(item, str):
        allowed_names.add(item)
    elif isinstance(item, (list, tuple)) and item:
        allowed_names.add(str(item[0]))
        allowed_names.add(str(item[1]))

# Don't hard-block if ROLE_PAGES differs; keep it usable
# if (page_name not in allowed_names) and (page_name not in allowed):
#     st.error("⛔ Access denied.")
#     st.stop()

# ---------------- UI ----------------
apply_talentiq_sidebar_style()
render_sidebar()

st.title("📊 Scoring Dashboard")

reviews = get_reviews()
if not reviews:
    st.warning("No reviews found yet. Create a review first.")
    render_footer()
    st.stop()

review_labels = [f"{r[1]} (#{r[0]})" for r in reviews]
review_map = {label: r[0] for label, r in zip(review_labels, reviews)}

selected = st.selectbox("Select Review", review_labels, index=0)
review_id = review_map[selected]
st.session_state["active_review"] = review_id

# Load KPI definitions + inputs
kpis = load_kpis()  # from data/kpi_definitions.json
inputs = get_kpi_inputs(review_id) or {}  # dict(kpi_id -> value)

st.subheader("Scoring Engine")

# ---------------- Compute ----------------
compute = st.button("✅ Compute Scores")

# Always compute for display (even if button not pressed) to avoid blanks
kpi_scores = {}
pillar_scores = {}

# KPI scores
for kpi_id, cfg in (kpis or {}).items():
    raw_val = inputs.get(kpi_id, 0.0)
    val = _to_float(raw_val, 0.0)
    kpi_scores[kpi_id] = _score_value(val, cfg)

# Pillar averages
pillar_bucket = {}
for kpi_id, cfg in (kpis or {}).items():
    pillar = str(cfg.get("pillar") or "").strip().upper()
    pillar_bucket.setdefault(pillar, []).append(kpi_scores.get(kpi_id, 0.0))

for pillar, scores_list in pillar_bucket.items():
    pillar_scores[pillar] = round(_mean(scores_list), 2)

# Business Health Index (mean of pillar averages)
bhi = round(_mean(list(pillar_scores.values())), 2)

# ---------------- Display ----------------
st.markdown("### 📋 KPI Scores")
# show as simple table
kpi_rows = []
for kpi_id, cfg in (kpis or {}).items():
    kpi_rows.append(
        {
            "KPI": f"{cfg.get('name','')} ({kpi_id})",
            "Input Value": round(_to_float(inputs.get(kpi_id, 0.0), 0.0), 4),
            "Score (1-5)": round(_to_float(kpi_scores.get(kpi_id, 0.0), 0.0), 2),
            "Pillar": (cfg.get("pillar") or "").strip(),
        }
    )
st.dataframe(kpi_rows, use_container_width=True)

st.markdown("### 📊 Pillar Averages")
pillar_rows = [{"Pillar": p, "Average Score": v} for p, v in pillar_scores.items()]
st.dataframe(pillar_rows, use_container_width=True)

st.markdown("### 🧭 Business Health Index (BHI)")
st.metric("BHI", bhi)

# ---------------- Export ----------------
st.subheader("📄 Board Report Export")

# Debug view (keep, but normalized)
st.caption(f"DEBUG ROLE RAW: {role_raw}")
st.caption(f"DEBUG ROLE NORMALIZED: {role}")

is_admin_or_ceo = role in ("admin", "ceo")

# If your project has billing rules for analysts, keep it.
can_export_ok = True
try:
    from core.billing_engine import can_export  # keep existing if present
    user_id = st.session_state["user"].get("id")
    if not is_admin_or_ceo:
        can_export_ok = bool(can_export(user_id))
except Exception:
    # If billing_engine not available, do not block
    can_export_ok = True

if not is_admin_or_ceo:
    st.info("Only Admins and CEOs can export official reports.")
else:
    # Admin/CEO bypass export limits
    if st.button("⬇️ Export Board Report"):
        # If you have a report generator, use it; else show a safe fallback.
        try:
            # Optional: your project may have a PDF exporter
            from core.board_report import generate_board_report_pdf  # type: ignore
            pdf_bytes = generate_board_report_pdf(review_id)
            st.download_button(
                "Download PDF",
                data=pdf_bytes,
                file_name=f"board_report_review_{review_id}.pdf",
                mime="application/pdf",
            )
        except Exception:
            # fallback: downloadable CSV-like text
            report_text = []
            report_text.append(f"REVIEW_ID,{review_id}")
            report_text.append(f"BHI,{bhi}")
            for p, v in pillar_scores.items():
                report_text.append(f"PILLAR_{p},{v}")
            st.download_button(
                "Download Summary (CSV)",
                data="\n".join(report_text).encode("utf-8"),
                file_name=f"board_report_review_{review_id}.csv",
                mime="text/csv",
            )
        st.success("✅ Export prepared.")

render_footer()
