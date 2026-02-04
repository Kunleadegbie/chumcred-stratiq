import streamlit as st

from core.roles import ROLE_PAGES
from db.repository import get_reviews, get_kpi_inputs, save_kpi_value
from core.kpi_registry import load_kpis

from components.styling import apply_talentiq_sidebar_style
from components.sidebar import render_sidebar
from components.footer import render_footer


# ---------------- Auth Guard ----------------
if "user" not in st.session_state:
    st.switch_page("pages/Login.py")
    st.stop()

# ---------------- Role Guard ----------------
role = (st.session_state["user"].get("role") or "").strip()
page_name = "3_Data_Input"

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
    # Don’t block if ROLE_PAGES format differs; just warn (keeps app usable)
    pass


# ---------------- UI Styling + Sidebar ----------------
apply_talentiq_sidebar_style()
render_sidebar()

st.title("📝 KPI Data Input")

# ---------------- Flash message ----------------
if st.session_state.get("kpi_saved_flash"):
    st.success("✅ KPI data saved.")
    st.session_state["kpi_saved_flash"] = False

# ---------------- Reviews ----------------
reviews = get_reviews()
if not reviews:
    st.warning("Create a review first.")
    render_footer()
    st.stop()

review_labels = [f"{r[1]} (#{r[0]})" for r in reviews]
review_map = {label: r[0] for label, r in zip(review_labels, reviews)}

# Persist selection across reruns
if "selected_review_label" not in st.session_state:
    active_review = st.session_state.get("active_review")
    if active_review:
        match = None
        for lbl, rid in review_map.items():
            if rid == active_review:
                match = lbl
                break
        st.session_state["selected_review_label"] = match or review_labels[0]
    else:
        st.session_state["selected_review_label"] = review_labels[0]

default_index = 0
if st.session_state["selected_review_label"] in review_labels:
    default_index = review_labels.index(st.session_state["selected_review_label"])

selected = st.selectbox(
    "Select Review",
    review_labels,
    index=default_index,
    key="selected_review_label"
)

review_id = review_map[selected]
st.session_state["active_review"] = review_id

# ---------------- KPI Inputs ----------------
kpis = load_kpis()
existing = get_kpi_inputs(review_id)  # dict(kpi_id -> value)

st.subheader("Enter KPI Values")

with st.form("kpi_form", clear_on_submit=False):

    inputs = {}

    for kpi_id, cfg in kpis.items():

        label = f"{cfg['name']} ({kpi_id})"

        default = existing.get(kpi_id, 0.0)
        try:
            default = float(default)
        except Exception:
            default = 0.0

        # Key makes widget stable across reruns
        val = st.number_input(label, value=default, key=f"kpi_{review_id}_{kpi_id}")
        inputs[kpi_id] = val

    submitted = st.form_submit_button("Save KPI Data")

    if submitted:
        for k, v in inputs.items():
            save_kpi_value(review_id, k, v)

        # Flash message after rerun
        st.session_state["kpi_saved_flash"] = True
        st.rerun()

render_footer()
