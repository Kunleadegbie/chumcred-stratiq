# ==================================================
# pages/9_Advisor.py — Business Advisor (Stable)
# ==================================================

import streamlit as st

from core.billing_engine import can_use_advisor
from core.advisor_engine import ask_business_advisor

from db.repository import get_reviews

from components.sidebar import render_sidebar
from components.styling import apply_talentiq_sidebar_style


# ==================================================
# AUTH
# ==================================================

if "user" not in st.session_state:
    st.switch_page("pages/Login.py")
    st.stop()


user = st.session_state["user"]
role = user["role"]
user_id = user["id"]


# ==================================================
# ROLE CONTROL
# ==================================================

if role not in ("Admin", "CEO"):
    st.error("⛔ Advisor access restricted to Admin and CEO.")
    st.stop()


# ==================================================
# BILLING CONTROL
# ==================================================

if not can_use_advisor(user_id, role):

    st.warning("🔒 Business Advisor Locked")

    st.info("Upgrade to Pro or Enterprise to unlock AI consulting.")

    if st.button("Upgrade Plan"):

        st.switch_page("pages/10_Subscription.py")

    render_sidebar()

    st.stop()

# ==================================================
# UI SETUP (ONCE ONLY)
# ==================================================

apply_talentiq_sidebar_style()
render_sidebar()


st.title("🧠 Business Advisor")


# ==================================================
# LOAD REVIEWS
# ==================================================

reviews = get_reviews()

if not reviews:
    st.warning("No reviews available.")
    st.stop()


review_map = {
    f"{r[1]} (#{r[0]})": r[0]
    for r in reviews
}


selected = st.selectbox(
    "Select Company Review",
    list(review_map.keys())
)


review_id = review_map[selected]


# ==================================================
# QUESTION INPUT
# ==================================================

st.subheader("Ask a Business Question")


question = st.text_input(
    "Type your question",
    placeholder="e.g. Why is our profitability weak?"
)


if st.button("Ask Advisor", use_container_width=True):

    if not question.strip():
        st.warning("Please enter a question.")
        st.stop()


    with st.spinner("Analyzing business data..."):

        answer = ask_business_advisor(
            review_id,
            question
        )


    st.success("Advisor Response")

    st.write(answer)

# other imports
from components.footer import render_footer

# page code ...

render_footer()

