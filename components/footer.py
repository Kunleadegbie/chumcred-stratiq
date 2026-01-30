# components/footer.py

import streamlit as st


def render_footer():

    st.markdown("---")

    st.markdown(
        """
        <div style="text-align:center; font-size:13px; color: #6c757d; padding: 10px;">
            Powered by <strong>Chumcred StratIQ</strong> — AI-Powered Business & Financial Intelligence Platform
        </div>
        """,
        unsafe_allow_html=True
    )
