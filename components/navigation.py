import streamlit as st


# ==========================================================
# ROLE-BASED PAGE ACCESS
# ==========================================================

ROLE_PAGES = {

    "Admin": [
        ("🏠 Home", "pages/1_Home.py"),
        ("📝 New Review", "pages/2_New_Review.py"),
        ("📊 Data Input", "pages/3_Data_Input.py"),
        ("📈 Scoring", "pages/4_Scoring_Dashboard.py"),
        ("📉 Benchmarking", "pages/5_Benchmarking.py"),
        ("🧩 SWOT", "pages/6_SWOT.py"),
        ("📑 Recommendations", "pages/7_Recommendations.py"),
        ("🤖 Advisor", "pages/9_Advisor.py"),
        ("⚙️ Admin Config", "pages/8_Admin_Config.py"),
        ("💰 Financial Analyzer", "pages/11_Financial_Analyzer.py"),
    ],

    "CEO": [
        ("🏠 Home", "pages/1_Home.py"),
        ("📈 Scoring", "pages/4_Scoring_Dashboard.py"),
        ("📉 Benchmarking", "pages/5_Benchmarking.py"),
        ("📑 Recommendations", "pages/7_Recommendations.py"),
        ("🤖 Advisor", "pages/9_Advisor.py"),
        ("💰 Financial Analyzer", "pages/11_Financial_Analyzer.py"),
    ],

    "Analyst": [
        ("🏠 Home", "pages/1_Home.py"),
        ("📝 New Review", "pages/2_New_Review.py"),
        ("📊 Data Input", "pages/3_Data_Input.py"),
        ("📈 Scoring", "pages/4_Scoring_Dashboard.py"),
        ("🤖 Advisor", "pages/9_Advisor.py"),
        ("💰 Financial Analyzer", "pages/11_Financial_Analyzer.py"),
    ],
}


# ==========================================================
# SAFE PAGE NAVIGATION
# ==========================================================

def safe_page_link(path, label):

    try:
        if st.button(label, use_container_width=True):
            st.switch_page(path)

    except Exception as e:
        st.error(f"Navigation error: {e}")
