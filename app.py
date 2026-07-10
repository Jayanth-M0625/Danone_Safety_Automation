import os
import streamlit as st

# Base directory of this script to resolve relative paths correctly
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_path(filename):
    return os.path.join(BASE_DIR, "CSFA", filename)

# Page config
st.set_page_config(
    page_title="Danone Safety Dashboards",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom premium CSS injection (exactly preserved from original)
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<style>
    /* Global styles */
    html, body, [class*="css"] {
        font-family: 'Danone One', 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    }
    
    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 1.5rem;
    }
    
    /* Header section styling */
    .dashboard-header {
        background: linear-gradient(135deg, #002256 0%, #00428c 100%);
        padding: 18px 25px;
        border-radius: 8px;
        color: white;
        margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(0, 34, 86, 0.1);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .header-title-box {
        display: flex;
        flex-direction: column;
    }
    .header-main-title {
        font-size: 22px;
        font-weight: 800;
        letter-spacing: 0.3px;
        margin: 0;
        text-transform: uppercase;
        font-family: 'Danone One', 'Inter', sans-serif;
    }
    .header-sub-title {
        font-size: 12px;
        font-weight: 400;
        opacity: 0.85;
        margin-top: 2px;
    }
    .header-info-box {
        text-align: right;
        background: rgba(255, 255, 255, 0.1);
        padding: 8px 12px;
        border-radius: 6px;
        backdrop-filter: blur(5px);
        border: 1px solid rgba(255, 255, 255, 0.15);
    }
    .header-info-date {
        font-size: 12px;
        font-weight: 600;
    }
    .header-info-lbl {
        font-size: 10px;
        opacity: 0.75;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* Target Streamlit's native border container for styling & equal-height layout */
    div[data-testid="stVerticalBlockBorderDiv"] {
        background-color: white !important;
        border-radius: 8px !important;
        border: 1px solid #e2e8f0 !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05) !important;
        padding: 15px !important;
        min-height: 150px !important;
    }

    /* Sidebar styles */
    [data-testid="stSidebar"] {
        background-color: #001233;
        color: white;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
        color: white;
    }
    
    /* Logo container white background */
    [data-testid="stSidebar"] [data-testid="stImage"] {
        background-color: white !important;
        padding: 12px 18px !important;
        border-radius: 6px !important;
        margin-bottom: 20px !important;
        border: 1px solid #e2e8f0 !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.15) !important;
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
    }
    
    /* Sidebar text/inputs style overrides */
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] h4,
    [data-testid="stSidebar"] h5,
    [data-testid="stSidebar"] h6 {
        color: #ffffff !important;
        font-family: "Danone One", "Inter", sans-serif !important;
        font-weight: 600 !important;
    }
    
    [data-testid="stSidebar"] button {
        background-color: #0033a0 !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
    }
    [data-testid="stSidebar"] button:hover {
        background-color: #002060 !important;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.3) !important;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- SIDEBAR ORCHESTRATION -----------------

# Logo rendering
logo_path = get_path("danone_logo.png")
if os.path.exists(logo_path):
    st.sidebar.image(logo_path, use_container_width=True)

st.sidebar.markdown("<h3 style='text-align: center; color: white;'>📋 DASHBOARD SELECT</h3>", unsafe_allow_html=True)

# Menu selector - PTW, CSFA, Tools & Tackles, Workplan
active_dashboard = st.sidebar.selectbox(
    "Active Dashboard",
    [
        "🛡️ CSFA Dashboard",
        "📋 PTW Dashboard",
        "🛠️ Tools & Tackles Dashboard",
        "📅 Workplan Dashboard"
    ],
    label_visibility="collapsed"
)
st.sidebar.markdown("<hr style='border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)

# ----------------- ROUTING -----------------

if active_dashboard == "🛡️ CSFA Dashboard":
    from dashboards.csfa_dashboard import render_csfa_dashboard
    render_csfa_dashboard()

elif active_dashboard == "📋 PTW Dashboard":
    from dashboards.ptw_dashboard import render_ptw_dashboard
    render_ptw_dashboard()

elif active_dashboard == "🛠️ Tools & Tackles Dashboard":
    from dashboards.tools_tackles_dashboard import render_tools_tackles_dashboard
    render_tools_tackles_dashboard()

else:  # active_dashboard == "📅 Workplan Dashboard"
    from dashboards.workplan_dashboard import render_workplan_dashboard
    render_workplan_dashboard()
