# pages/4_Scoring_Dashboard.py
import math
import streamlit as st

from core.roles import ROLE_PAGES
from core.kpi_registry import load_kpis
from db.repository import get_reviews, get_kpi_inputs

from components.styling import apply_talentiq_sidebar_style
from components.sidebar import render_sidebar
from components.footer import render_footer

# Optional billing export gate
try:
    from core.billing_engine import can_export  # record_export removed (it doesn't exist)
except Exception:
    can_export = None


def _safe_float(x, default=0.0) -> float:
    try:
        if x is None:
            return default
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return default
        return v
    except Exception:
        return default


def _norm_role(role_val) -> str:
    return str(role_val or "").strip().lower()


def _score_from_rules(value: float, rules: list) -> int:
    """
    rules example:
      {"min": null, "max": 0, "score": 1}
      {"min": 1, "max": 5, "score": 2}
    """
    v = _safe_float(value, 0.0)
    for r in rules or []:
        rmin = r.get("min", None)
        rmax = r.get("max", None)
        score = int(r.get("score", 0))

        ok_min = True if rmin is None else (v >= float(rmin))
        ok_max = True if rmax is None else (v <= float(rmax))
        if ok_min and ok_max:
            return score
    return 0


# ---------------- Auth Guard ----------------
if "user" not in st.session_state:
    st.switch_page("pages/Login.py")
    st.stop()

# ---------------- Role Guard ----------------
role_raw = st.session_state["user"].get("role")
role = _norm_role(role_raw)
page_name = "4_Scoring_Dashboard"
allowed = ROLE_PAGES.get(role_raw, ROLE_PAGES.get(role, []))  # tolerate old mapping styles

if allowed and page_name not in allowed:
    # Keep usable (your other pages do same)
    pass

# ---------------- UI ----------------
apply_talentiq_sidebar_style()
render_sidebar()

st.title("📈 Scoring Dashboard")

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

kpi_defs = load_kpis()
inputs = get_kpi_inputs(review_id)  # dict(kpi_id -> value)

if not inputs:
    st.warning("⚠️ No KPI inputs found for this review.")
    st.info("Go to **KPI Data Input** and save KPI values first.")
    render_footer()
    st.stop()

st.subheader("Scoring Engine")

# ---------------- Compute KPI scores ----------------
kpi_scores = {}
pillar_scores = {}  # pillar -> list[int]

for kpi_id, cfg in kpi_defs.items():
    val = _safe_float(inputs.get(kpi_id, 0.0), 0.0)

    rules = cfg.get("scoring_rules", [])
    score = _score_from_rules(val, rules)

    kpi_scores[kpi_id] = {"value": val, "score": score, "pillar": cfg.get("pillar", "UNKNOWN")}

    pillar = str(cfg.get("pillar", "UNKNOWN"))
    pillar_scores.setdefault(pillar, []).append(score)

# ---------------- Pillar averages ----------------
pillar_avgs = {}
for pillar, scores in pillar_scores.items():
    if scores:
        pillar_avgs[pillar] = round(sum(scores) / len(scores), 2)
    else:
        pillar_avgs[pillar] = 0.0

# ---------------- BHI ----------------
all_scores = [v["score"] for v in kpi_scores.values() if isinstance(v.get("score"), int)]
bhi = round(sum(all_scores) / len(all_scores), 2) if all_scores else 0.0

# ---------------- Display ----------------
st.subheader("📋 KPI Scores")
for kpi_id, obj in kpi_scores.items():
    st.write(f"**{kpi_id}** — Value: `{round(obj['value'], 2)}` | Score: `{obj['score']}`")

st.subheader("📊 Pillar Averages")
for p, avg in pillar_avgs.items():
    st.metric(p, avg)

st.subheader("Business Health Index (BHI)")
st.metric("BHI", bhi)

# ---------------- Board Report Export Gate ----------------
st.subheader("📄 Board Report Export")

# debug
st.caption(f"DEBUG ROLE RAW: {role_raw}")
st.caption(f"DEBUG ROLE NORMALIZED: {role}")

is_admin_or_ceo = role in ("admin", "ceo")

if not is_admin_or_ceo:
    st.warning("Only Admins and CEOs can export official reports.")
    render_footer()
    st.stop()

# can_export gate (if billing engine exists)
user_id = st.session_state["user"].get("id")

if callable(can_export):
    allowed_export = bool(can_export(user_id))
else:
    # if billing is not wired, don't block admin export
    allowed_export = True

if not allowed_export:
    st.warning("Export limit reached or export not enabled for this account.")
    render_footer()
    st.stop()

# If you already have a report exporter function, call it here.
# For now, provide a placeholder "Export" button so the gate works.
if st.button("Export Board Report"):
    st.success("✅ Export allowed. (Hook your PDF generator here.)")

render_footer()
