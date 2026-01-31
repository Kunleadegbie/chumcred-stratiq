import streamlit as st


def apply_talentiq_sidebar_style():

    st.markdown(
        """
        <style>

        /* Hide Streamlit multipage nav */
        [data-testid="stSidebarNav"] {
            display: none !important;
        }

        /* Hide menu / footer */
        #MainMenu { visibility: hidden; }
        header { visibility: hidden; }
        footer { visibility: hidden; }

        /* Sidebar padding */
        section[data-testid="stSidebar"] > div {
            padding-top: 0.8rem;
        }

        /* Sidebar border */
        section[data-testid="stSidebar"] {
            border-right: 1px solid rgba(49,51,63,0.2);
        }

        </style>
        """,
        unsafe_allow_html=True
    )
