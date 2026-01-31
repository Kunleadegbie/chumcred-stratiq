import streamlit as st

from core.roles import ROLE_PAGES
from db.repository import get_reviews, get_kpi_inputs, save_kpi_value
from core.kpi_registry import load_kpis


# ---------------- Auth Guard ----------------
if "user" not in st.session_state:
    st.switch_page("pages/Login.py")
    st.stop()


# ---------------- Role Guard ----------------
role = st.session_state["user"]["role"]

page_name = "3_Data_Input"

if page_name not in ROLE_PAGES.get(role, []):
    st.error("⛔ Access denied.")
    st.stop()

from components.styling import apply_talentiq_sidebar_style
apply_talentiq_sidebar_style()

# ---------------- Sidebar ----------------
from components.sidebar import render_sidebar
render_sidebar()


# ---------------- Main ----------------
st.title("📝 KPI Data Input")

reviews = get_reviews()

if not reviews:
    st.warning("Create a review first.")
    st.stop()


review_map = {
    f"{r[1]} (#{r[0]})": r[0]
    for r in reviews
}

selected = st.selectbox(
    "Select Review",
    list(review_map.keys())
)

review_id = review_map[selected]

st.session_state["active_review"] = review_id


kpis = load_kpis()

existing = get_kpi_inputs(review_id)

st.subheader("Enter KPI Values")


with st.form("kpi_form"):

    inputs = {}

    for kpi_id, cfg in kpis.items():

        label = f"{cfg['name']} ({kpi_id})"

        default = float(existing.get(kpi_id, 0.0)) if existing else 0.0

        val = st.number_input(
            label,
            value=float(default),
            key=f"kpi_{review_id}_{kpi_id}"
        )


        inputs[kpi_id] = val


    submitted = st.form_submit_button("Save KPI Data")

    if submitted:

        for k, v in inputs.items():
            save_kpi_value(review_id, k, v)

        st.success("KPI data saved.")

# other imports
from components.footer import render_footer

# page code ...

render_footer()

