# ==================================================
# pages/11_Financial_Analyzer.py — Financial Analyzer
# ==================================================

import os
import streamlit as st

from core.financial_engine import analyze_financials
from core.excel_parser import parse_financial_excel
from core.finance_advisor import generate_finance_insights
from core.finance_alerts import generate_finance_alerts

from db.repository import (
    save_financial_kpis,
    save_financial_raw,
    load_financial_raw,
    get_reviews,
    get_kpi_inputs
)

from components.sidebar import render_sidebar
from components.styling import apply_talentiq_sidebar_style
from components.finance_charts import *


# ==================================================
# PAGE CONFIG
# ==================================================

st.set_page_config(
    page_title="Financial Analyzer",
    layout="wide"
)


# ==================================================
# AUTH GUARD
# ==================================================

if "user" not in st.session_state:
    st.switch_page("pages/Login.py")
    st.stop()


# ==================================================
# ACTIVE REVIEW (SURVIVE RELOAD)
# ==================================================

# On browser refresh, Streamlit session_state may be empty on Railway.
# Instead of forcing New Review, recover by selecting the latest review.
if "active_review" not in st.session_state:
    reviews = get_reviews()
    if reviews:
        st.session_state["active_review"] = reviews[0][0]  # latest (ORDER BY id DESC)
    else:
        st.warning("Create a review first.")
        st.switch_page("pages/2_New_Review.py")
        st.stop()


# ==================================================
# SESSION INIT (PERSISTENCE)
# ==================================================

if "fin_excel" not in st.session_state:
    saved = load_financial_raw(st.session_state["active_review"])
    st.session_state["fin_excel"] = saved if saved else {}

if "finance_results" not in st.session_state:
    # If we already saved KPIs to DB before, preload them so they show after reload
    existing = get_kpi_inputs(st.session_state["active_review"]) or {}
    preload = {}
    if "FIN_REV_GROWTH" in existing:
        preload["FIN_REV_GROWTH"] = float(existing.get("FIN_REV_GROWTH") or 0.0)
    if "FIN_PROFIT_MARGIN" in existing:
        preload["FIN_PROFIT_MARGIN"] = float(existing.get("FIN_PROFIT_MARGIN") or 0.0)
    st.session_state["finance_results"] = preload if preload else None

if "finance_insights" not in st.session_state:
    st.session_state["finance_insights"] = []

if "finance_alerts" not in st.session_state:
    st.session_state["finance_alerts"] = []


# ==================================================
# UI SETUP
# ==================================================

apply_talentiq_sidebar_style()
render_sidebar()

st.title("📊 Financial Analyzer (3-Year Trend)")


# ==================================================
# PATHS
# ==================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TEMPLATE_PATH = os.path.join(
    BASE_DIR,
    "data",
    "templates",
    "financial_template.xlsx"
)


# ==================================================
# SAFE GETTER
# ==================================================

def get_val(key, idx=None, default=0.0):

    data = st.session_state.get("fin_excel", {})

    try:
        if idx is None:
            return float(data.get(key, default))
        return float(data.get(key, [default])[idx])
    except Exception:
        return float(default)


# ==================================================
# DOWNLOAD TEMPLATE
# ==================================================

st.subheader("📥 Excel Template")

if os.path.exists(TEMPLATE_PATH):

    with open(TEMPLATE_PATH, "rb") as f:

        st.download_button(
            "Download Financial Template",
            f,
            file_name="financial_template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

else:
    st.error("Financial template not found. Contact Admin.")


# ==================================================
# EXCEL UPLOAD
# ==================================================

st.subheader("📤 Upload Completed Template")

uploaded = st.file_uploader(
    "Upload Excel File",
    type=["xlsx"]
)

if uploaded:

    try:

        parsed = parse_financial_excel(uploaded)

        st.success("Template validated successfully.")

        rev = parsed["Income_Statement"]
        bs = parsed["Balance_Sheet"]
        cf = parsed["Cash_Flow"]

        data = {

            "rev": [
                rev["Revenue"][0],
                rev["Revenue"][1],
                rev["Revenue"][2]
            ],

            "ebitda": [
                rev["EBITDA"][0],
                rev["EBITDA"][1],
                rev["EBITDA"][2]
            ],

            "profit": [
                rev["Net Profit"][0],
                rev["Net Profit"][1],
                rev["Net Profit"][2]
            ],

            "assets": bs["Total Assets"][0],
            "equity": bs["Equity"][0],

            "current_assets": bs["Current Assets"][0],
            "current_liabilities": bs["Current Liabilities"][0],

            "debt": bs["Total Debt"][0],

            "ocf": cf["Operating Cash Flow"][0],
            "capex": cf["CAPEX"][0]
        }

        # Save permanently
        save_financial_raw(
            st.session_state["active_review"],
            data
        )

        st.session_state["fin_excel"] = data

    except Exception as e:
        st.error(str(e))


# ==================================================
# INCOME STATEMENT
# ==================================================

st.subheader("Income Statement (3 Years)")

c1, c2, c3 = st.columns(3)

with c1:
    rev_y2 = st.number_input("Revenue (Y-2)", 0.0, value=get_val("rev", 0))
    ebitda_y2 = st.number_input("EBITDA (Y-2)", 0.0, value=get_val("ebitda", 0))
    profit_y2 = st.number_input("Net Profit (Y-2)", 0.0, value=get_val("profit", 0))

with c2:
    rev_y1 = st.number_input("Revenue (Y-1)", 0.0, value=get_val("rev", 1))
    ebitda_y1 = st.number_input("EBITDA (Y-1)", 0.0, value=get_val("ebitda", 1))
    profit_y1 = st.number_input("Net Profit (Y-1)", 0.0, value=get_val("profit", 1))

with c3:
    rev_y = st.number_input("Revenue (Y)", 0.0, value=get_val("rev", 2))
    ebitda_y = st.number_input("EBITDA (Y)", 0.0, value=get_val("ebitda", 2))
    profit_y = st.number_input("Net Profit (Y)", 0.0, value=get_val("profit", 2))


# ==================================================
# BALANCE SHEET
# ==================================================

st.subheader("Balance Sheet")

b1, b2, b3 = st.columns(3)

with b1:
    assets = st.number_input("Total Assets", 0.0, value=get_val("assets"))
    equity = st.number_input("Equity", 0.0, value=get_val("equity"))

with b2:
    current_assets = st.number_input("Current Assets", 0.0, value=get_val("current_assets"))
    current_liabilities = st.number_input("Current Liabilities", 0.0, value=get_val("current_liabilities"))

with b3:
    debt = st.number_input("Total Debt", 0.0, value=get_val("debt"))


# ==================================================
# CASH FLOW
# ==================================================

st.subheader("Cash Flow")

cf1, cf2 = st.columns(2)

with cf1:
    ocf = st.number_input("Operating Cash Flow", 0.0, value=get_val("ocf"))

with cf2:
    capex = st.number_input("CAPEX", 0.0, value=get_val("capex"))


# ==================================================
# ANALYZE
# ==================================================

st.divider()

if st.button("📈 Analyze Financials"):

    data = {

        "rev": [rev_y2, rev_y1, rev_y],
        "ebitda": [ebitda_y2, ebitda_y1, ebitda_y],
        "profit": [profit_y2, profit_y1, profit_y],

        "assets": assets,
        "equity": equity,

        "current_assets": current_assets,
        "current_liabilities": current_liabilities,

        "debt": debt,

        "ocf": ocf,
        "capex": capex
    }

    # Save raw permanently
    save_financial_raw(
        st.session_state["active_review"],
        data
    )

    st.session_state["fin_excel"] = data

    results = analyze_financials(data)

    if not results:
        st.error("Financial analysis failed.")
        st.stop()

    # ==================================================
    # KPI Mapping (ALIGN WITH data/kpi_definitions.json)
    # ==================================================
    # FIN_REV_GROWTH   -> Revenue Growth (YoY) in percent
    # FIN_PROFIT_MARGIN -> Profit Margin (Net Profit / Revenue) in percent

    rev_curr = float(rev_y) if rev_y else 0.0
    rev_prev = float(rev_y1) if rev_y1 else 0.0
    prof_curr = float(profit_y) if profit_y else 0.0

    if rev_prev != 0:
        fin_rev_growth = ((rev_curr - rev_prev) / rev_prev) * 100.0
    else:
        fin_rev_growth = 0.0

    if rev_curr != 0:
        fin_profit_margin = (prof_curr / rev_curr) * 100.0
    else:
        fin_profit_margin = 0.0

    kpi_payload = {
        "FIN_REV_GROWTH": round(fin_rev_growth, 2),
        "FIN_PROFIT_MARGIN": round(fin_profit_margin, 2)
    }

    # Save KPIs
    save_financial_kpis(
        st.session_state["active_review"],
        kpi_payload
    )

    # Persist for display
    st.session_state["finance_results"] = kpi_payload
    st.session_state["finance_insights"] = generate_finance_insights(results)
    st.session_state["finance_alerts"] = generate_finance_alerts(results)

    st.success("✅ Financial KPIs calculated and saved")


# ==================================================
# RESULTS
# ==================================================

if st.session_state.get("finance_results"):

    st.subheader("📌 Calculated Financial KPIs (Aligned with KPI Definitions)")

    kpis = st.session_state["finance_results"]

    # Nice display + easy to copy manually
    colA, colB = st.columns(2)
    with colA:
        st.metric("FIN_REV_GROWTH (Revenue Growth YoY %)", kpis.get("FIN_REV_GROWTH", 0.0))
    with colB:
        st.metric("FIN_PROFIT_MARGIN (Profit Margin %)", kpis.get("FIN_PROFIT_MARGIN", 0.0))

    st.caption("These KPIs are saved to the database and should appear in the Data Input page for the same review.")

    # ---------------- Charts ----------------

    st.subheader("📊 Board Financial Charts")

    col1, col2 = st.columns(2)

    with col1:
        st.pyplot(plot_revenue([rev_y2, rev_y1, rev_y]))
        st.pyplot(plot_profit([profit_y2, profit_y1, profit_y]))

    with col2:
        st.pyplot(plot_ebitda_margin(
            [rev_y2, rev_y1, rev_y],
            [ebitda_y2, ebitda_y1, ebitda_y]
        ))
        st.pyplot(plot_debt_ratio(debt, assets))

    col3, col4 = st.columns(2)

    with col3:
        st.pyplot(plot_current_ratio(current_assets, current_liabilities))

    with col4:
        st.pyplot(plot_cashflow(ocf, capex))

    # ---------------- AI Advisor ----------------

    st.subheader("🤖 AI Financial Advisor")

    for msg in st.session_state.get("finance_insights", []):
        st.info(msg)

    # ---------------- Alerts ----------------

    st.subheader("🚨 Risk Alerts")

    if not st.session_state.get("finance_alerts"):
        st.success("No critical financial risks detected.")

    for level, msg in st.session_state.get("finance_alerts", []):

        if level == "CRITICAL":
            st.error(msg)
        elif level == "HIGH":
            st.warning(msg)
        else:
            st.info(msg)


# ==================================================
# SEND TO KPI
# ==================================================

st.divider()

if st.button("➡️ Send to KPI Input"):

    if not st.session_state.get("finance_results"):
        st.error("Run financial analysis first.")
        st.stop()

    st.switch_page("pages/3_Data_Input.py")
