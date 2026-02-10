import streamlit as st

from core.roles import ROLE_PAGES
from components.styling import apply_talentiq_sidebar_style
from components.sidebar import render_sidebar
from components.footer import render_footer


# ---------------- Auth Guard ----------------
if "user" not in st.session_state:
    st.switch_page("pages/Login.py")
    st.stop()


# ---------------- Role Guard ----------------
role = (st.session_state["user"].get("role") or "").strip()
page_name = "1_Home"

allowed = ROLE_PAGES.get(role, [])
if page_name not in allowed:
    st.error("⛔ Access denied.")
    st.stop()


# ---------------- UI Styling + Sidebar ----------------
apply_talentiq_sidebar_style()
render_sidebar()

st.title("Welcome to the Corporate Diagnostic Dashboard")


# ==========================================================
# MARKDOWN: WHAT THE APP DOES
# ==========================================================

st.markdown("""
## What this app is about

This platform helps corporate organizations **measure business health**, spot risks early, and make better decisions using a structured, KPI-driven diagnostic framework.

Instead of relying on gut-feel or scattered reports, the app provides a **single view of organizational performance** across key pillars and produces **board-ready outputs** (scores, pillar averages, and a Business Health Index).

## The challenge it solves

Many organizations struggle with:
- **Disconnected performance data** (Finance, Operations, People, Customer metrics living in different places)
- **Inconsistent measurement** (different teams calculate KPIs differently)
- **Delayed visibility** (issues show up late—after revenue drops, customers churn, or costs spike)
- **No standard scoring** to compare performance over time or across business units

This app solves that by:
- Standardizing KPI definitions (from `data/kpi_definitions.json`)
- Applying consistent scoring rules
- Computing pillar averages and an overall **Business Health Index (BHI)**
- Supporting analysis workflows like **Financial Analyzer**, **Scoring Dashboard**, **Benchmarking**, and optional reporting/export

## Benefits to a corporate organization

Using the platform, you can expect:
- **Clear diagnostic snapshot** of business performance
- **Early warning signals** (where performance is weakening)
- **Standardized scoring** for leadership conversations and board reporting
- **Consistency across teams**, locations, or departments
- **Trend tracking** across multiple review periods (monthly, quarterly, yearly)

## What to expect when using the app (recommended flow)

1. **Create a Review** (Company + Industry)
2. **Enter KPI values** on the Data Input page (or allow auto-fill from Financial Analyzer where applicable)
3. Run the **Scoring Dashboard** to compute:
   - KPI Scores
   - Pillar Averages
   - Business Health Index (BHI)
4. Use **Benchmarking / SWOT / other pages** to interpret results
5. Export/reporting (if enabled for your role/subscription)
""")


# ==========================================================
# MARKDOWN: KPI EXPLANATIONS
# ==========================================================

st.markdown("## KPI guide (so you know what to enter)")

st.info(
    "Tip: Most KPIs here are percentages. Enter them as a percent number (e.g., enter 12.5 for 12.5%). "
    "The exact KPIs shown on your Data Input page come from `data/kpi_definitions.json`."
)

with st.expander("📌 Revenue Growth (YoY) — FIN_REV_GROWTH", expanded=True):
    st.markdown("""
**What it means:** How much revenue increased (or decreased) compared to the previous year.  
**Why it matters:** Shows whether the business is expanding or contracting.  
**Typical calculation:**  
- `((Revenue this year − Revenue last year) / Revenue last year) × 100`

**How to interpret:**
- Higher is usually better (steady positive growth signals demand and competitiveness).
- Negative growth may indicate market pressure, customer loss, or weak execution.
""")

with st.expander("📌 Profit Margin — FIN_PROFIT_MARGIN", expanded=False):
    st.markdown("""
**What it means:** The share of revenue that remains as profit after costs.  
**Why it matters:** A company can grow revenue and still be unhealthy if profitability is weak.  
**Typical calculation:**  
- `(Net Profit / Revenue) × 100`

**How to interpret:**
- Higher is better (more efficient cost management and pricing power).
- Low margins may signal high costs, pricing issues, or inefficiencies.
""")

with st.expander("📌 Customer Churn Rate — CUST_CHURN", expanded=False):
    st.markdown("""
**What it means:** The percentage of customers who stopped using your product/service within a period.  
**Why it matters:** High churn is a strong signal of dissatisfaction, competition, or weak retention strategy.  
**Typical calculation:**  
- `(Customers lost during period / Customers at start of period) × 100`

**How to interpret:**
- Lower is better.
- Rising churn often predicts revenue decline if not corrected.
""")

with st.expander("📌 Operating Cost Ratio — OPS_COST_RATIO", expanded=False):
    st.markdown("""
**What it means:** The share of revenue consumed by operating costs.  
**Why it matters:** Measures operational efficiency and cost discipline.  
**Typical calculation (common form):**  
- `(Operating Expenses / Revenue) × 100`

**How to interpret:**
- Lower is better.
- A high ratio may signal inefficiency, waste, or operating model problems.
""")

with st.expander("📌 Employee Attrition Rate — PEOPLE_ATTRITION", expanded=False):
    st.markdown("""
**What it means:** The percentage of employees who leave over a period.  
**Why it matters:** High attrition increases hiring/training costs and can reduce execution quality.  
**Typical calculation:**  
- `(Employees who left / Average number of employees) × 100`

**How to interpret:**
- Lower is better.
- Persistent attrition can indicate culture issues, weak leadership, poor compensation, or burnout.
""")

st.markdown("""
> If your Data Input page shows an additional KPI beyond the ones listed above, it is defined in your `data/kpi_definitions.json`.
> Share that KPI name/ID and I’ll add it here in the same format so users understand it clearly.
""")

render_footer()
