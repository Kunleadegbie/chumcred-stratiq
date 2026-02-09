import streamlit as st

from core.roles import ROLE_PAGES
from db.repository import get_reviews

from components.styling import apply_talentiq_sidebar_style
from components.sidebar import render_sidebar
from components.footer import render_footer


# ---------------- Auth Guard ----------------
if "user" not in st.session_state:
    st.switch_page("pages/Login.py")
    st.stop()


# ---------------- Role Guard (robust) ----------------
role = (st.session_state["user"].get("role") or "").strip()
page_name = "1_Home"

allowed = ROLE_PAGES.get(role, [])
# Support both formats: list[str] OR list[tuple(label,path)]
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


# ---------------- UI Styling + Sidebar ----------------
apply_talentiq_sidebar_style()
render_sidebar()


# ---------------- Main ----------------
st.title("🏠 Welcome to the Business Health Diagnostic (BHD)")

st.markdown(
    """
## What this app is about

This platform helps organizations **measure business health**, **diagnose performance gaps**, and **produce board-ready insights**
using a structured KPI framework across key pillars (e.g., Financial, Customer, Operations, People).

It is designed for leadership teams who want a **clear, consistent, data-driven view** of performance—without relying on scattered spreadsheets.

---

## The challenges this app helps solve

- **Fragmented KPIs:** KPIs often live in different files and departments, making it hard to get one reliable view.
- **No consistent scoring:** Teams struggle to translate raw KPI values into an objective performance score.
- **Slow reporting:** Preparing management/board reports takes time and often lacks consistency.
- **Decision delays:** Without a structured diagnostic view, issues are discovered too late.

---

## Benefits to any corporate organization

- **Standardized assessment:** Same KPI definitions and scoring rules applied every time.
- **Faster decision-making:** Clear KPI scores, pillar averages, and overall Business Health Index (BHI).
- **Improved accountability:** Everyone sees what is measured and what “good” looks like.
- **Board-ready outputs:** Cleaner reporting that supports executive discussions and action plans.

---

## What you should expect when using the app

1. **Create a Review** (New Review) – choose the company/unit and industry.
2. **Enter KPI Values** (Data Input) – supply your KPI values for the review period.
3. **Financial Analyzer** – upload/enter financials and generate financial KPIs + AI insights.
4. **Scoring Dashboard** – compute KPI scores, pillar averages, and the Business Health Index (BHI).
5. **Benchmarking** – compare performance to industry reference benchmarks (where available).
6. **Board Report Export** – generate a management/board-ready report for sharing.

---
"""
)

# ---------------- KPI Glossary (auto from the same registry used in Data Input) ----------------
st.subheader("📘 KPI Guide (What each KPI means)")

try:
    from core.kpi_registry import load_kpis
    kpis = load_kpis() or {}
except Exception:
    kpis = {}

if not kpis:
    st.info(
        "KPI definitions could not be loaded. "
        "If this persists, confirm `data/kpi_definitions.json` exists and `core/kpi_registry.py` can read it."
    )
else:
    st.markdown(
        """
Below are the KPIs used in the **Data Input** page. Read these definitions carefully so you understand
what you are entering and how it affects scoring.
"""
    )

    # group by pillar if present
    by_pillar = {}
    for kpi_id, cfg in kpis.items():
        pillar = str(cfg.get("pillar", "GENERAL")).strip() or "GENERAL"
        by_pillar.setdefault(pillar, []).append((kpi_id, cfg))

    for pillar in sorted(by_pillar.keys()):
        with st.expander(f"📌 {pillar.title()} KPIs", expanded=True):
            for kpi_id, cfg in sorted(by_pillar[pillar], key=lambda x: x[0]):
                name = cfg.get("name", kpi_id)
                unit = cfg.get("unit", "")
                direction = cfg.get("direction", "")

                # friendly, practical explanations for your known KPI IDs; fallback for others
                extra = ""
                if kpi_id == "FIN_REV_GROWTH":
                    extra = (
                        "- **Meaning:** Year-on-year change in revenue.\n"
                        "- **Why it matters:** Shows whether the business is expanding or shrinking.\n"
                        "- **How to estimate:** `((Revenue this year - Revenue last year) / Revenue last year) * 100`.\n"
                        "- **Tip:** Use audited/management accounts; ensure same period comparison.\n"
                    )
                elif kpi_id == "FIN_PROFIT_MARGIN":
                    extra = (
                        "- **Meaning:** Percentage of revenue that becomes profit.\n"
                        "- **Why it matters:** Measures profitability and cost discipline.\n"
                        "- **How to estimate:** `(Net Profit / Revenue) * 100`.\n"
                        "- **Tip:** If profit is negative, margin will be negative—this will lower the score.\n"
                    )
                elif kpi_id == "CUST_CHURN":
                    extra = (
                        "- **Meaning:** Percentage of customers who stop using your product/service in a period.\n"
                        "- **Why it matters:** High churn signals service issues, pricing problems, or competition pressure.\n"
                        "- **How to estimate:** `(Customers lost during period / Customers at start) * 100`.\n"
                        "- **Tip:** Define “active customer” clearly (e.g., active in last 30/90 days).\n"
                    )
                elif kpi_id == "OPS_COST_RATIO":
                    extra = (
                        "- **Meaning:** Operating costs as a percentage of revenue.\n"
                        "- **Why it matters:** Indicates operational efficiency.\n"
                        "- **How to estimate:** `(Operating Costs / Revenue) * 100`.\n"
                        "- **Tip:** Ensure you consistently include/exclude the same cost items each time.\n"
                    )
                elif kpi_id == "PEOPLE_ATTRITION":
                    extra = (
                        "- **Meaning:** Percentage of employees who leave during a period.\n"
                        "- **Why it matters:** High attrition affects performance, culture, and cost (replacement/training).\n"
                        "- **How to estimate:** `(Number of leavers / Average headcount) * 100`.\n"
                        "- **Tip:** Use HR records; treat involuntary vs voluntary exits consistently.\n"
                    )
                else:
                    extra = (
                        "- **Meaning:** Enter the KPI value for the review period based on your internal measurement.\n"
                        "- **Tip:** Keep measurement definitions consistent across periods for fair scoring.\n"
                    )

                st.markdown(
                    f"""
### {name} (`{kpi_id}`)
- **Unit:** `{unit}`  
- **Scoring direction:** `{direction}`  

{extra}
"""
                )

st.divider()

# ---------------- Reviews ----------------
st.subheader("📂 Existing Reviews")

reviews = get_reviews()

if not reviews:
    st.info("No reviews yet. Create one to begin.")
else:
    for r in reviews:
        st.write(f"#{r[0]} | {r[1]} ({r[2]}) | {r[3]}")

st.divider()
st.markdown("➡ Go to **New Review** to create a new assessment.")


render_footer()
