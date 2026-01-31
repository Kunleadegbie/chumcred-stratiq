
# ==================================================
# pages/2_New_Review.py — Create New Review
# ==================================================

import streamlit as st

from db.repository import create_review
from core.billing_engine import can_create_review

from components.sidebar import render_sidebar
from components.styling import apply_talentiq_sidebar_style


# ==================================================
# PAGE CONFIG (MUST BE FIRST)
# ==================================================

st.set_page_config(
    page_title="New Review",
    layout="wide"
)


# ==================================================
# AUTH
# ==================================================

if "user" not in st.session_state:
    st.switch_page("pages/Login.py")
    st.stop()


user = st.session_state["user"]
user_id = user["id"]
role = user["role"]


# ==================================================
# BILLING CONTROL
# ==================================================

if role != "Admin" and not can_create_review(user_id, role):

    apply_talentiq_sidebar_style()
    render_sidebar()

    st.warning("🔒 Review limit reached.")

    st.info("Upgrade your plan to create more company reviews.")

    if st.button("Upgrade Plan"):
        st.switch_page("pages/10_Subscription.py")

    st.stop()


# ==================================================
# UI SETUP
# ==================================================

apply_talentiq_sidebar_style()
render_sidebar()

st.title("➕ Create New Company Review")


# ==================================================
# INDUSTRY OPTIONS (EXPANDED)
# ==================================================

industries = [
    "Telecom",
    "Banking",
    "FMCG",
    "Manufacturing",
    "Retail",
    "SME",
    "Logistics",
    "Healthcare",
    "Education",
    "Real Estate",
    "Agriculture",
    "Energy",
    "Government",
    "Construction",
    "Hospitality",
    "Transportation",
    "Mining",
    "ICT Services",
    "Insurance",
    "Consultancy",
    "Forex Trading",
    "Fintech"
]


# ==================================================
# REVIEW FORM
# ==================================================

with st.form("review_form"):

    st.subheader("Company Information")


    company_name = st.text_input(
        "Company Name",
        placeholder="e.g. Chumcred Limited"
    )


    industry = st.selectbox(
        "Industry",
        industries
    )


    submit = st.form_submit_button("Create Review")


# ==================================================
# SUBMIT HANDLER
# ==================================================

if submit:

    if not company_name.strip():

        st.warning("Please enter company name.")
        st.stop()


    review_id = create_review(
        company_name=company_name.strip(),
        industry=industry
    )


    st.success("✅ Review created successfully.")


    st.session_state["active_review"] = review_id


    st.switch_page("pages/3_Data_Input.py")
