"""SokoRadar: entry point. Run with `streamlit run app.py` from this folder."""
import streamlit as st

st.set_page_config(page_title="SokoRadar", page_icon=":material/radar:", layout="wide")

nav = st.navigation(
    [
        st.Page("app_pages/overview.py", title="This month", icon=":material/map:", default=True),
        st.Page("app_pages/market.py", title="Market check", icon=":material/storefront:"),
        st.Page("app_pages/proof.py", title="Does it work?", icon=":material/verified:"),
        st.Page("app_pages/about.py", title="About & limits", icon=":material/info:"),
    ]
)
nav.run()
