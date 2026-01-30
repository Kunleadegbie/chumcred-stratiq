
# ==================================================
# pages/8_Admin_Config.py — System Configuration
# ==================================================

import streamlit as st
import json
from pathlib import Path

from core.roles import ROLE_PAGES
from components.styling import apply_talentiq_sidebar_style
from components.sidebar import render_sidebar

from db.repository import (
    get_all_users,
    update_user_role,
    activate_user
)


# ==================================================
# AUTH GUARD
# ==================================================

if "user" not in st.session_state:
    st.switch_page("pages/Login.py")
    st.stop()


user = st.session_state["user"]
role = user["role"]

PAGE_NAME = "8_Admin_Config"

if PAGE_NAME not in ROLE_PAGES.get(role, []):
    st.error("⛔ Access denied.")
    st.stop()


# ==================================================
# UI SETUP
# ==================================================

apply_talentiq_sidebar_style()
render_sidebar()

st.title("⚙️ System Configuration (Admin)")
st.caption("Manage system settings and user governance")


# ==================================================
# PATHS
# ==================================================

BASE_DIR = Path(__file__).parents[1]
DATA_DIR = BASE_DIR / "data"

KPI_FILE = DATA_DIR / "kpi_definitions.json"
PILLAR_FILE = DATA_DIR / "pillar_weights.json"


# ==================================================
# HELPERS
# ==================================================

def load_json(path: Path):

    if not path.exists():
        return None

    try:
        with open(path) as f:
            return json.load(f)
    except Exception as e:
        return str(e)


def save_uploaded_file(upload, path: Path):

    content = upload.read()

    try:
        json.loads(content.decode())
    except Exception:
        return False, "Invalid JSON file."

    with open(path, "wb") as f:
        f.write(content)

    return True, "Uploaded successfully."


# ==================================================
# CONFIG STATUS
# ==================================================

st.subheader("📁 Configuration Status")

c1, c2 = st.columns(2)

with c1:
    st.write("KPI Definitions")
    st.success("✅ Found" if KPI_FILE.exists() else "❌ Missing")

with c2:
    st.write("Pillar Weights")
    st.success("✅ Found" if PILLAR_FILE.exists() else "❌ Missing")


st.divider()


# ==================================================
# VIEW FILES
# ==================================================

with st.expander("📊 View KPI Definitions"):
    st.json(load_json(KPI_FILE) or {})

with st.expander("📈 View Pillar Weights"):
    st.json(load_json(PILLAR_FILE) or {})


st.divider()


# ==================================================
# UPLOAD FILES
# ==================================================

st.subheader("⬆️ Upload Configuration")


kpi_upload = st.file_uploader("Upload KPI JSON", type=["json"])

if kpi_upload:

    ok, msg = save_uploaded_file(kpi_upload, KPI_FILE)

    st.success(msg) if ok else st.error(msg)

    if ok:
        st.rerun()


pillar_upload = st.file_uploader("Upload Pillar Weights JSON", type=["json"])

if pillar_upload:

    ok, msg = save_uploaded_file(pillar_upload, PILLAR_FILE)

    st.success(msg) if ok else st.error(msg)

    if ok:
        st.rerun()


st.divider()


# ==================================================
# VALIDATE CONFIG
# ==================================================

st.subheader("✅ Validate Configuration")

if st.button("Validate"):

    errors = []

    kpis = load_json(KPI_FILE)
    pillars = load_json(PILLAR_FILE)

    if not isinstance(kpis, dict):
        errors.append("Invalid KPI file.")

    if not isinstance(pillars, dict):
        errors.append("Invalid pillar file.")

    if isinstance(pillars, dict):

        total = sum(pillars.values())

        if abs(total - 1.0) > 0.05:
            errors.append("Pillar weights must sum to 1.")


    if errors:

        st.error("Configuration Errors:")

        for e in errors:
            st.write("•", e)

    else:
        st.success("Configuration OK.")


# ==================================================
# USER MANAGEMENT
# ==================================================

st.divider()
st.subheader("👥 User Management")


users = get_all_users()

ROLES = ["Pending", "Admin", "CEO", "Analyst"]


if not users:

    st.info("No users found.")

else:

    for u in users:

        col1, col2, col3 = st.columns([3,2,2])

        with col1:
            st.write(u["email"])

        with col2:

            current = u.get("role", "Pending")

            if current not in ROLES:
                current = "Pending"


            new_role = st.selectbox(
                "Role",
                ROLES,
                index=ROLES.index(current),
                key=f"role_{u['id']}"
            )

        with col3:

            if st.button("Update", key=f"btn_{u['id']}"):

                update_user_role(u["id"], new_role)

                # Auto-activate if approved
                if new_role != "Pending":
                    activate_user(u["id"])

                st.success("Updated")

                st.rerun()


# ==================================================
# PENDING APPROVALS
# ==================================================

st.divider()
st.subheader("⏳ Pending Approvals")


pending = [u for u in users if u["role"] == "Pending"]


if not pending:

    st.success("No pending users.")

else:

    for u in pending:

        c1, c2, c3 = st.columns([3,2,2])

        with c1:
            st.write(u["email"])

        with c2:

            assign_role = st.selectbox(
                "Assign Role",
                ["Analyst", "CEO"],
                key=f"pending_{u['id']}"
            )

        with c3:

            if st.button("Approve", key=f"approve_{u['id']}"):

                update_user_role(u["id"], assign_role)
                activate_user(u["id"])

                st.success("Approved")

                st.rerun()


# other imports
from components.footer import render_footer

# page code ...

render_footer()

