import streamlit as st

from db.repository import get_reviews

from components.styling import apply_talentiq_sidebar_style
from components.sidebar import render_sidebar


apply_talentiq_sidebar_style()
render_sidebar()

st.title("🏠 Home")


# ==================================================
# APP OVERVIEW (MARKDOWN)
# ==================================================

st.markdown(
    """
## Chumcred Business Diagnostic & KPI Scoring Platform

This app helps corporate organizations **diagnose business health** using a simple, structured workflow:

1. **Create a Review** (company + industry)
2. **Input KPI Values** (or send KPIs from Financial Analyzer)
3. **Generate Scores** (KPI scores → Pillar averages → Business Health Index)
4. **Benchmark** (optional industry comparisons)
5. **Export a Board-ready Report** (PDF report for leadership decisions)

---

### The challenge this app solves
Many organizations struggle with:
- KPI data scattered across teams (Finance, Operations, People, Customer)
- Lack of a consistent scoring method to interpret KPI numbers
- No single “business health” snapshot that leadership can use quickly
- Reports that are not standardized for board/management use

---

### Benefits to any corporate organization
Using this app, you can:
- **Standardize KPI assessment** across departments
- **Detect risk early** (weak pillars show up immediately)
- **Track improvement over time** through repeated reviews
- **Improve decision speed** with a single Business Health Index (BHI)
- **Generate leadership-ready reports** (consistent format)

---

### What you should expect when using this app
- A **guided workflow** from data input → scoring → insights
- **Saved data** per review (so refresh/reload doesn’t wipe entries)
- Clear KPI scoring and pillar summaries you can explain to executives
"""
)

st.divider()


# ==================================================
# KPI EXPLANATIONS (pull from KPI registry)
# ==================================================

st.markdown("## KPI Guide (What each KPI means)")

kpi_defs = {}
try:
    from core.kpi_registry import load_kpis  # local project module
    kpi_defs = load_kpis() or {}
except Exception:
    kpi_defs = {}

# Preferred order (matches your earlier definitions); we will show up to 6 KPIs.
preferred_order = [
    "FIN_REV_GROWTH",
    "FIN_PROFIT_MARGIN",
    "CUST_CHURN",
    "OPS_COST_RATIO",
    "PEOPLE_ATTRITION",
]

# Build display list: preferred first, then any remaining until we reach 6
ordered_ids = []
for k in preferred_order:
    if k in kpi_defs:
        ordered_ids.append(k)

for k in kpi_defs.keys():
    if k not in ordered_ids:
        ordered_ids.append(k)

ordered_ids = ordered_ids[:6]  # show 6 (as requested)

if not kpi_defs:
    st.info(
        "KPI definitions could not be loaded. "
        "Ensure `core/kpi_registry.py` can read `data/kpi_definitions.json`."
    )
else:
    for kpi_id in ordered_ids:
        cfg = kpi_defs.get(kpi_id, {})
        name = cfg.get("name", kpi_id)
        pillar = cfg.get("pillar", "—")
        unit = cfg.get("unit", "—")
        direction = cfg.get("direction", "—")

        # Friendly explanation defaults (keeps page useful even if JSON lacks descriptions)
        default_explainer = {
            "FIN_REV_GROWTH": (
                "Measures how fast revenue is growing year-on-year (YoY). "
                "Higher growth usually indicates stronger market demand and/or expansion."
            ),
            "FIN_PROFIT_MARGIN": (
                "Shows how much profit the company keeps from revenue after costs. "
                "Higher margins mean better efficiency and pricing power."
            ),
            "CUST_CHURN": (
                "The percentage of customers who stop using your service over a period. "
                "Lower churn means customers are staying and loyalty is improving."
            ),
            "OPS_COST_RATIO": (
                "Operating costs as a percentage of revenue (or total operating base). "
                "Lower ratio often means the business is running more efficiently."
            ),
            "PEOPLE_ATTRITION": (
                "The percentage of employees leaving the organization over a period. "
                "Lower attrition typically indicates better retention and culture stability."
            ),
        }

        explainer = default_explainer.get(kpi_id, "This KPI helps measure performance within its pillar.")

        st.markdown(
            f"""
### **{name}** (`{kpi_id}`)
- **Pillar:** {pillar}
- **Unit:** {unit}
- **Direction:** {direction}

**What it means:** {explainer}

**Tip:** Use real operational or audited sources (finance reports, HR attrition logs, customer churn analytics) for best accuracy.
"""
        )

st.divider()


# ==================================================
# EXISTING REVIEWS (your original content)
# ==================================================

st.subheader("📌 Existing Reviews")

reviews = get_reviews()

if not reviews:
    st.info("No reviews yet. Create one from **New Review**.")
else:
    for r in reviews:
        st.write(f"✅ {r[1]} — {r[2]}")
