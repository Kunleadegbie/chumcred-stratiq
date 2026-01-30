# ==================================================
# pages/10_Subscription.py — Subscription Plans
# ==================================================

import streamlit as st
import json
from datetime import date, timedelta

from db.repository import create_subscription
from core.billing_engine import get_active_plan

from components.sidebar import render_sidebar
from components.styling import apply_talentiq_sidebar_style


# ==================================================
# AUTH
# ==================================================

if "user" not in st.session_state:
    st.switch_page("pages/Login.py")
    st.stop()


user = st.session_state["user"]
user_id = user["id"]


# ==================================================
# UI
# ==================================================

apply_talentiq_sidebar_style()
render_sidebar()

st.title("💳 Subscription Plans")


# ==================================================
# LOAD PLANS
# ==================================================

with open("data/plans.json") as f:
    plans = json.load(f)


# ==================================================
# CURRENT PLAN
# ==================================================

current = get_active_plan(user_id)

if current:

    st.success(f"Active Plan: {current['plan']}")

    st.caption(
        f"Expires: {current['end_date']}"
    )

    st.divider()


# ==================================================
# PLANS DISPLAY
# ==================================================

cols = st.columns(len(plans))


for col, (plan, info) in zip(cols, plans.items()):

    with col:

        st.subheader(plan)

        st.metric("Price (₦)", f"{info['price']:,}")

        st.write(f"Max Reviews: {info['max_reviews']}")
        st.write(f"Max Exports: {info['max_exports']}")
        st.write(f"AI Advisor: {'Yes' if info['advisor'] else 'No'}")

        st.divider()


        if st.button(f"Subscribe to {plan}"):

            start = date.today()
            end = start + timedelta(days=365)

            create_subscription(
                user_id=user_id,
                plan=plan,
                start_date=start,
                end_date=end,
                max_reviews=info["max_reviews"],
                max_exports=info["max_exports"]
            )

            st.success(f"Subscribed to {plan}!")

            st.rerun()

# other imports
from components.footer import render_footer

# page code ...

render_footer()

