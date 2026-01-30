import streamlit as st

def apply_talentiq_sidebar_style():
    st.markdown(
        """
        <style>
        /* Hide Streamlit's default multipage navigation inside sidebar */
        [data-testid="stSidebarNav"] { display: none !important; }

        /* Hide Streamlit "hamburger"/toolbar/menu/header/footer clutter */
        #MainMenu { visibility: hidden; }
        header { visibility: hidden; }
        footer { visibility: hidden; }

        /* Optional: tighten sidebar padding for a cleaner look */
        section[data-testid="stSidebar"] > div { padding-top: 0.8rem; }

        /* Optional: make sidebar feel like an app panel */
        section[data-testid="stSidebar"] {
            border-right: 1px solid rgba(49, 51, 63, 0.2);
        }
        </style>
        """,
        unsafe_allow_html=True
    )
