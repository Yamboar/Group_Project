import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

st.set_page_config(
    page_title="XAI Operations Research System",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.sidebar.title("XAI-OR System")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigation",
    ["Home", "Transportation Problem", "Assignment Problem", "Saved Problems", "Help"],
    index=0,
)

if page == "Home":
    from presentation.pages import home
    home.render()
elif page == "Transportation Problem":
    from presentation.pages import transportation
    transportation.render()
elif page == "Assignment Problem":
    from presentation.pages import assignment
    assignment.render()
elif page == "Saved Problems":
    from presentation.pages import saved
    saved.render()
elif page == "Help":
    from presentation.pages import help_page
    help_page.render()
