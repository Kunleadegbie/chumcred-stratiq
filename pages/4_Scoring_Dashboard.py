import os
import math
import streamlit as st
import pandas as pd

from core.kpi_registry import load_kpis
from core.roles import ROLE_PAGES
from core.scoring_engine import compute_scores
from core.billing_engine import can_export, record_export
from core.report_engine import export_board_report

from db.repository import get_reviews, get_kpi_inputs, save_scores, get_scores

from components.styling import apply_talentiq_sidebar_style
from components.sidebar import render_sidebar
from components.footer import render_footer


# ==========================================================
# HELPERS
# ==========================================================

def _to_float(x, default=0.0):
    try:
        if x is None:
            return float(default)
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return float(default)
        return v
    except Exception:
        return float(default)


def _safe_basename(path: str) -> str:
    try:
        return os.path.basename(path)
    except Exception:
        return "report.pdf"


# ==========================================================
# AUTH GUARD
# ==========================================================

if "user" not in st.session_state:
    st.switch_page("pages/Login.py")
    st.stop()

user = st.session_state["user"] or {}
user_id = user.get("id")
user_role = (user.get("role") or "").strip()

# ==========================================================
# ROLE GUARD (non-blocking)
# ==========================================================

page_name = "4_Scoring_Dashboard"
allowed = ROLE_PAGES.get(user_role, [])

allowed_names = set()
for item in allowed:
    if isinstance(item, str):
        allowed_names.add(item)
    elif isinstance(item, (list, tuple)) and item:
        allowed_names.add(str(item[0]))
        allowed_names.add(str(item[1]))

if (page_name not in allowed_names) and (page_name not in allowed):
    # Keep app usable across ROLE_PAGES formats
    pass


# ==========================================================
# UI
# ==========================================================

apply_talentiq_sidebar_style()
render_sidebar()

st.title("📈 Scoring Dashboard")

# ==========================================================
# REVIEWS
# ==========================================================

reviews = get_reviews()
if not reviews:
    st.warning("Create a review first.")
    render_footer()
    st.stop()

# Ensure active_review exists
if "active_review" not in st.session_state or st.session_state.get("active_review") is None:
    st.session_state["active_review"] = reviews[0][0]

review_id = int(st.session_state["active_review"])

# ==========================================================
# LOAD KPI DEFINITIONS + INPUTS
# ==========================================================

kpis = load_kpis()
inputs = get_kpi_inputs(review_id) or {}  # dict(kpi_id -> value)

# Ensure every KPI key exists (prevents missing -> NaN paths)
for kpi_id in kpis.keys():
    inputs.setdefault(kpi_id, 0.0)

# Coerce inputs to floats
inputs = {k: _to_float(v, 0.0) for k, v in inputs.items()}

# ==========================================================
# SCORE NOW
# ==========================================================

st.subheader("Run Scoring")

colA, colB = st.columns([1, 2])

with colA:
    if st.button("🧮 Compute Scores", use_container_width=True):
        try:
            results, pillars, bhi = compute_scores(inputs, kpis)

            # --- Sanitize NaNs before saving ---
            clean_results = []
            for r in (results or []):
                clean_results.append({
                    "kpi_id": str(r.get("kpi_id") or ""),
                    "pillar": str(r.get("pillar") or ""),
                    "value": _to_float(r.get("value"), 0.0),
                    "score": _to_float(r.get("score"), 0.0),
                })

            clean_pillars = {}
            for p, v in (pillars or {}).items():
                clean_pillars[str(p)] = _to_float(v, 0.0)

            bhi = _to_float(bhi, 0.0)

            save_scores(review_id, clean_results, clean_pillars, bhi)
            st.success("✅ Scores computed and saved.")
            st.rerun()

        except Exception as e:
            st.error(f"Failed to compute scores: {e}")

with colB:
    st.caption("Scoring uses KPI definitions (direction + scoring rules). Missing KPI values default to 0 to avoid NaN results.")


# ==========================================================
# DISPLAY SCORES (FROM DB)
# ==========================================================

saved_scores = get_scores(review_id) or []

if not saved_scores:
    st.info("No saved scores yet. Click **Compute Scores** to generate results.")
    render_footer()
    st.stop()

df = pd.DataFrame(saved_scores, columns=["kpi_id", "pillar", "value", "score"])

# Clean any legacy NaNs (from previous runs)
df["value"] = df["value"].apply(lambda x: _to_float(x, 0.0))
df["score"] = df["score"].apply(lambda x: _to_float(x, 0.0))
df["pillar"] = df["pillar"].fillna("").astype(str)
df["kpi_id"] = df["kpi_id"].fillna("").astype(str)

st.subheader("KPI Scores")
st.dataframe(df, use_container_width=True, hide_index=True)

# Pillar averages
pillar_df = df.groupby("pillar", as_index=False)["score"].mean()
pillar_df["score"] = pillar_df["score"].apply(lambda x: _to_float(x, 0.0))

st.subheader("Pillar Averages")
st.dataframe(pillar_df.rename(columns={"score": "average_score"}), use_container_width=True, hide_index=True)

# Business Health Index (average of pillar averages)
bhi = _to_float(pillar_df["score"].mean() if not pillar_df.empty else 0.0, 0.0)

st.subheader("Business Health Index (BHI)")
st.metric("BHI", round(bhi, 2))


# ==========================================================
# BOARD REPORT EXPORT
# ==========================================================

st.divider()
st.subheader("Board Report Export")

# Debug role (helps you verify Railway user_role)
st.caption(f"DEBUG ROLE: {user_role or '(empty)'}")

is_admin = (user_role or "").strip().lower() in ("admin", "ceo")

# can_export is optional gating (billing). We do NOT block Admin/CEO if billing is misconfigured.
has_export = True
try:
    has_export = bool(can_export(user_id))
except Exception:
    has_export = True

if not is_admin:
    st.info("Only Admins and CEOs can export official reports.")
else:
    if not has_export:
        st.warning("Export limit/billing check failed, but export is allowed for Admin/CEO to keep operations running.")

    if st.button("📄 Export Official Board Report"):
        try:
            file_path = export_board_report(review_id, official=True)
            if not file_path:
                st.error("Report generation failed.")
            else:
                with open(file_path, "rb") as f:
                    st.download_button(
                        "⬇️ Download Board Report",
                        f,
                        file_name=_safe_basename(file_path),
                        mime="application/pdf",
                    )

                # record export (best-effort)
                try:
                    record_export(user_id)
                except Exception:
                    pass

        except Exception as e:
            st.error(f"Export failed: {e}")

render_footer()
