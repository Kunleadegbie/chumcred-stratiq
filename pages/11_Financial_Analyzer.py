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
    save_ai_report
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

if "active_review" not in st.session_state:
    st.warning("Create a review first.")
    st.switch_page("pages/2_New_Review.py")
    st.stop()


# ==================================================
# SESSION INIT (PERSISTENCE)
# ==================================================

if "fin_excel" not in st.session_state:

    saved = load_financial_raw(st.session_state["active_review"])

    if saved:
        st.session_state["fin_excel"] = saved
    else:
        st.session_state["fin_excel"] = {}

if "finance_results" not in st.session_state:
    st.session_state["finance_results"] = None

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
            "capex": cf["CAPEX"][0],

            # manual KPI placeholders saved for reload (if user sets them later)
            "cust_churn": float(st.session_state.get("fin_excel", {}).get("cust_churn", 0.0) or 0.0),
            "ops_cost_ratio": float(st.session_state.get("fin_excel", {}).get("ops_cost_ratio", 0.0) or 0.0),
            "people_attrition": float(st.session_state.get("fin_excel", {}).get("people_attrition", 0.0) or 0.0),
        }

        # Save permanently for reload/navigation
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
# OTHER KPI INPUTS (MANUAL)
# ==================================================

st.subheader("Other KPI Inputs (Manual)")

m1, m2, m3 = st.columns(3)

with m1:
    cust_churn = st.number_input(
        "Customer Churn Rate (%)",
        0.0,
        value=float(st.session_state.get("fin_excel", {}).get("cust_churn", 0.0) or 0.0)
    )

with m2:
    ops_cost_ratio = st.number_input(
        "Operating Cost Ratio (%)",
        0.0,
        value=float(st.session_state.get("fin_excel", {}).get("ops_cost_ratio", 0.0) or 0.0)
    )

with m3:
    people_attrition = st.number_input(
        "Employee Attrition Rate (%)",
        0.0,
        value=float(st.session_state.get("fin_excel", {}).get("people_attrition", 0.0) or 0.0)
    )


# ==================================================
# ANALYZE
# ==================================================

st.divider()

def _safe_pct(numer: float, denom: float) -> float:
    try:
        denom = float(denom)
        if denom == 0:
            return 0.0
        return (float(numer) / denom) * 100.0
    except Exception:
        return 0.0


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
        "capex": capex,

        # manual KPIs saved too
        "cust_churn": cust_churn,
        "ops_cost_ratio": ops_cost_ratio,
        "people_attrition": people_attrition
    }

    # Save raw permanently (reload persistence)
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
    # KPI Mapping (MATCHES kpi_definitions.json)
    # ==================================================
    # FIN_REV_GROWTH: Revenue Growth (YoY) using last 2 years (Y vs Y-1)
    rev_growth_yoy = _safe_pct((rev_y - rev_y1), rev_y1)

    # FIN_PROFIT_MARGIN: Profit Margin (%) on latest year
    profit_margin = _safe_pct(profit_y, rev_y)

    kpi_payload = {
        "FIN_REV_GROWTH": round(rev_growth_yoy, 2),
        "FIN_PROFIT_MARGIN": round(profit_margin, 2),
        "CUST_CHURN": round(float(cust_churn or 0.0), 2),
        "OPS_COST_RATIO": round(float(ops_cost_ratio or 0.0), 2),
        "PEOPLE_ATTRITION": round(float(people_attrition or 0.0), 2),
    }

    # Save KPIs to DB (so Data Input shows them)
    save_financial_kpis(
        st.session_state["active_review"],
        kpi_payload
    )

    # Save AI Insights/Alerts to DB for Board Report PDF
    insights = generate_finance_insights(results) or []
    alerts = generate_finance_alerts(results) or []

    save_ai_report(
        st.session_state["active_review"],
        "financial_analyzer",
        {"insights": insights, "alerts": alerts}
    )

    # Save for UI
    st.session_state["finance_results"] = kpi_payload
    st.session_state["finance_insights"] = insights
    st.session_state["finance_alerts"] = alerts

    st.success("✅ Financial KPIs calculated and saved")


# ==================================================
# RESULTS
# ==================================================

if st.session_state.get("finance_results"):

    st.subheader("📌 Calculated KPIs (Saved to Data Input)")

    kpis = st.session_state["finance_results"]
    for k, v in kpis.items():
        st.metric(k, v)

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
    for msg in (st.session_state.get("finance_insights") or []):
        st.info(msg)

    # ---------------- Alerts ----------------
    st.subheader("🚨 Risk Alerts")

    if not st.session_state.get("finance_alerts"):
        st.success("No critical financial risks detected.")

    for level, msg in (st.session_state.get("finance_alerts") or []):
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
