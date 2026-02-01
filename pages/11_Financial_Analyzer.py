# ==================================================
# pages/11_Financial_Analyzer.py — Financial Analyzer
# ==================================================

import os
import streamlit as st

from core.financial_engine import analyze_financials
from core.excel_parser import parse_financial_excel
from core.finance_advisor import generate_finance_insights
from core.finance_alerts import generate_finance_alerts

from db.repository import save_financial_kpis, get_kpi_inputs

from components.sidebar import render_sidebar
from components.styling import apply_talentiq_sidebar_style
from components.finance_charts import *

from components.footer import render_footer


# ==================================================
# PAGE CONFIG (FIRST CALL)
# ==================================================

st.set_page_config(
    page_title="Financial Analyzer",
    layout="wide"
)


# ==================================================
# SESSION STATE INIT
# ==================================================

if "fin_excel" not in st.session_state:
    st.session_state["fin_excel"] = {}

if "finance_results" not in st.session_state:
    st.session_state["finance_results"] = None

if "finance_insights" not in st.session_state:
    st.session_state["finance_insights"] = []

if "finance_alerts" not in st.session_state:
    st.session_state["finance_alerts"] = []

if "finance_kpi_payload" not in st.session_state:
    st.session_state["finance_kpi_payload"] = {}


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
# SAFE VALUE GETTER
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

uploaded = st.file_uploader("Upload Excel File", type=["xlsx"])

if uploaded:
    try:
        parsed = parse_financial_excel(uploaded)
        st.success("Template validated successfully.")

        rev = parsed["Income_Statement"]
        bs = parsed["Balance_Sheet"]
        cf = parsed["Cash_Flow"]

        st.session_state["fin_excel"] = {
            "rev": [rev["Revenue"][0], rev["Revenue"][1], rev["Revenue"][2]],
            "ebitda": [rev["EBITDA"][0], rev["EBITDA"][1], rev["EBITDA"][2]],
            "profit": [rev["Net Profit"][0], rev["Net Profit"][1], rev["Net Profit"][2]],
            "assets": bs["Total Assets"][0],
            "equity": bs["Equity"][0],
            "current_assets": bs["Current Assets"][0],
            "current_liabilities": bs["Current Liabilities"][0],
            "debt": bs["Total Debt"][0],
            "ocf": cf["Operating Cash Flow"][0],
            "capex": cf["CAPEX"][0],
        }

        st.info("Excel values loaded into the form below. Click **Analyze Financials** to generate KPIs.")
        st.rerun()

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

    st.session_state["fin_excel"] = data

    results = analyze_financials(data)

    st.session_state["finance_results"] = results
    st.session_state["finance_insights"] = generate_finance_insights(results)
    st.session_state["finance_alerts"] = generate_finance_alerts(results)

    # Map Financial Results → KPI IDs (the exact ones you listed)
    kpi_payload = {
        "FIN_REV_GROWTH_YOY": round(float(results.get("rev_cagr", 0) or 0), 2),
        "FIN_EBITDA_MARGIN": round(float(results.get("ebitda_margin", 0) or 0), 2),
        "FIN_NET_MARGIN": round(float(results.get("net_margin", 0) or 0), 2),
        "FIN_ROA": round(float(results.get("roa", 0) or 0), 2),
        "FIN_ROE": round(float(results.get("roe", 0) or 0), 2),
        "FIN_CURRENT_RATIO": round(float(results.get("current_ratio", 0) or 0), 2),
        "FIN_DEBT_RATIO": round(float(results.get("debt_ratio", 0) or 0), 2),
    }

    st.session_state["finance_kpi_payload"] = kpi_payload

    st.success("✅ Financial Analysis Completed")
    st.rerun()


# ==================================================
# RESULTS
# ==================================================

if st.session_state.get("finance_results"):

    results = st.session_state["finance_results"]

    st.subheader("✅ Financial KPI Output (Auto-calculated)")

    # Always show the KPI payload clearly (manual copy fallback)
    kpi_payload = st.session_state.get("finance_kpi_payload", {})
    if kpi_payload:
        st.dataframe(
            [{"KPI_ID": k, "Value": v} for k, v in kpi_payload.items()],
            use_container_width=True
        )
    else:
        st.info("Click **Analyze Financials** to generate KPI output.")

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

    insights = st.session_state.get("finance_insights", [])
    if not insights:
        st.info("No AI insights yet. Run **Analyze Financials**.")
    else:
        for msg in insights:
            st.info(msg)

    # ---------------- Alerts ----------------
    st.subheader("🚨 Risk Alerts")

    alerts = st.session_state.get("finance_alerts", [])
    if not alerts:
        st.success("No critical financial risks detected.")
    else:
        for level, msg in alerts:
            if level == "CRITICAL":
                st.error(msg)
            elif level == "HIGH":
                st.warning(msg)
            else:
                st.info(msg)

    # ---------------- SEND TO KPI ----------------
    st.divider()

    if st.button("➡️ Send to KPI Input"):

        kpi_payload = st.session_state.get("finance_kpi_payload", {})
        if not kpi_payload:
            st.error("Run financial analysis first.")
            render_footer()
            st.stop()

        save_financial_kpis(
            st.session_state["active_review"],
            kpi_payload
        )

        st.success("✅ Financial KPIs saved to database and ready in Data Input.")
        st.switch_page("pages/3_Data_Input.py")

render_footer()
