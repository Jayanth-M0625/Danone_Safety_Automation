import streamlit as st

# Configure the main app pages configuration
st.set_page_config(
    page_title="Safety Dashboards Portal - Danone",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Define pages for the dashboard portal
csfa_page = st.Page(
    page="CSFA/app.py",
    title="Contractor Safety Field Audits (CSFA)",
    icon="🛡️",
    default=True
)

ptw_page = st.Page(
    page="PTW/app.py",
    title="Permit to Work (PTW)",
    icon="📝"
)

workplan_page = st.Page(
    page="Workplan/app.py",
    title="Workplan",
    icon="📋"
)

powertools_page = st.Page(
    page="Power_tools/app.py",
    title="Power Tools",
    icon="⚡"
)

# Navigation sidebar configuration
pg = st.navigation(
    {
        "Safety Dashboards": [csfa_page, ptw_page, workplan_page, powertools_page]
    }
)

# Run navigation
pg.run()
