import os
import json
import pandas as pd
import numpy as np
import openpyxl
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

# Base directory of this script to resolve relative paths correctly
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_path(filename):
    return os.path.join(BASE_DIR, "CSFA", filename)

def get_ptw_path(filename):
    return os.path.join(BASE_DIR, "PTW", filename)

def get_workplan_path(filename):
    return os.path.join(BASE_DIR, "Workplan", filename)

# Configuration Loader to dynamically load paths
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            try:
                return json.load(f)
            except:
                return {}
    return {}

def save_config(config_data):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config_data, f)

# Page config
st.set_page_config(
    page_title="Danone Safety Dashboards",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom premium CSS injection
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

# ----------------- CSFA DATA PIPELINE FUNCTIONS -----------------

def normalize_text(text):
    if pd.isna(text):
        return ""
    return "".join(c.lower() for c in str(text) if c.isalnum())

@st.cache_data(ttl=60)
def load_data(csfa_path=None):
    if csfa_path is None:
        config = load_config()
        csfa_path = config.get("csfa_path", get_path("CSFA Accumilative data.xlsx"))

    if not os.path.exists(csfa_path):
        return pd.DataFrame()
        
    df = pd.read_excel(csfa_path, sheet_name="CSFA Accumilative data")
    df = df[df['Observation Discription '].notna()]
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df['Severity'] = pd.to_numeric(df['Severity '], errors='coerce').fillna(0).astype(int)
    df['unsafe acts'] = pd.to_numeric(df['unsafe acts'], errors='coerce').fillna(0).astype(int)
    df['unsafe Condes'] = pd.to_numeric(df['unsafe Condes'], errors='coerce').fillna(0).astype(int)
    df['Status'] = df['Status'].astype(str).str.strip()
    df['Contractor name'] = df['Contractor name'].astype(str).str.strip()
    df['Trend'] = df['Trend'].astype(str).str.strip()
    df['Zone'] = df['Zone'].astype(str).str.strip()
    return df

# ----------------- PTW DATA PIPELINE FUNCTIONS -----------------

@st.cache_data(ttl=60)
def load_ptw_data(ptw_path, ptw_audit_path):
    if not os.path.exists(ptw_path) or not os.path.exists(ptw_audit_path):
        return None, None
    try:
        df_ptw = pd.read_excel(ptw_path)
        df_audit = pd.read_excel(ptw_audit_path)
        
        # Clean column names
        df_ptw.columns = df_ptw.columns.str.strip()
        df_audit.columns = df_audit.columns.str.strip()
        
        # Parse dates
        df_ptw['PTW Date'] = pd.to_datetime(df_ptw['PTW Date'], errors='coerce')
        df_audit['Date'] = pd.to_datetime(df_audit['Date'], errors='coerce')
        
        return df_ptw, df_audit
    except Exception as e:
        return None, None

# ----------------- HTML RENDER HELPERS -----------------

def generate_html_table(title, headers, rows):
    header_cols_html = "".join(f"<th style='background-color:#002256; color:white; padding:8px 10px; border: 1px solid #e2e8f0; text-align:center; font-size:12px; font-weight:700; text-transform:uppercase;'>{h}</th>" for h in headers)
    
    rows_html = ""
    for r in rows:
        row_cols_html = ""
        for i, val in enumerate(r):
            align = "center" if i == 0 or isinstance(val, (int, float)) or (isinstance(val, str) and val.isdigit()) else "left"
            row_cols_html += f"<td style='padding:8px 10px; border: 1px solid #e2e8f0; text-align:{align}; font-size:12.5px; color:#334155; font-family:\"Danone One\", \"Inter\", sans-serif;'>{val}</td>"
        rows_html += f"<tr>{row_cols_html}</tr>"
        
    html = f"""
    <div style='margin-bottom:20px; border-radius:8px; overflow:hidden; border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,0.05);'>
        <div style='background-color:#002256; color:white; padding:10px 12px; font-size:13px; font-weight:700; text-align:center; letter-spacing:0.5px; text-transform:uppercase; font-family:\"Danone One\", \"Inter\", sans-serif;'>
            {title}
        </div>
        <table style='width:100%; border-collapse:collapse; background-color:#ffffff;'>
            <thead>
                <tr>{header_cols_html}</tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
    </div>
    """
    return html

def render_kpi_metric(title, emoji, value, color, subtitle=None):
    # Adjust subtitle styling if present
    sub_html = ""
    if subtitle:
        # Check if trend is upward/positive and use appropriate badge colors
        badge_bg = "#e8f5e9" if "▲" in subtitle or "✅" in subtitle or "+" in subtitle else "#f1f5f9"
        badge_text = "#2e7d32" if "▲" in subtitle or "✅" in subtitle or "+" in subtitle else "#475569"
        sub_html = f"<div style='font-size:10px; font-weight:600; color:{badge_text}; background-color:{badge_bg}; padding:2px 8px; border-radius:4px; margin-top:6px; display:inline-block;'>{subtitle}</div>"
        
    html = f"""<div style="text-align: left; display: flex; flex-direction: column; justify-content: space-between; height: 120px; font-family: 'Danone One', 'Inter', -apple-system, sans-serif; padding: 5px 0;">
<div style="display: flex; justify-content: space-between; align-items: flex-start; width: 100%;">
<div style="font-size: 11px; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; line-height: 1.3; max-width: 80%;">{title}</div>
<div style="font-size: 14px; background-color: #f8fafc; width: 26px; height: 26px; border-radius: 6px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; border: 1px solid #e2e8f0; box-shadow: 0 1px 2px rgba(0,0,0,0.02);">{emoji}</div>
</div>
<div>
<div style="font-size: 26px; font-weight: 800; color: {color}; line-height: 1.1; letter-spacing: -0.5px;">{value}</div>
{sub_html}
</div>
</div>"""
    st.markdown(html, unsafe_allow_html=True)

# ----------------- PTW HTML RENDER HELPERS -----------------

def render_donut_chart(compliance_val):
    fig = go.Figure(data=[go.Pie(
        labels=['Compliance', 'Gap'],
        values=[compliance_val, 100 - compliance_val],
        hole=.7,
        marker=dict(colors=['#10b981', '#f1f5f9']),
        textinfo='none',
        hoverinfo='label+percent'
    )])
    
    fig.update_layout(
        showlegend=False,
        annotations=[dict(
            text=f"<span style='font-size:32px; font-weight:800; color:#10b981; font-family:\"Danone One\", Inter, sans-serif;'>{compliance_val}%</span>",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=20)
        )],
        margin=dict(l=10, r=10, t=10, b=10),
        height=180,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    return fig

# ----------------- PTW STATIC DATA -----------------

STATIC_PTW = {
    'total_issued': 1235,
    'total_closed': 1224,
    'total_audited': 97,
    'total_observations': 148,
    'critical_observations': 67,
    'compliance': 89,
    'compliance_donut': 89,
    'high_risk_issued': 169,
    'high_risk_safely_executed': 169,
    'high_risk_observations': 16,
    'violators': [
        [1, 'Fluid-line', 28],
        [2, 'Crescon', 18],
        [3, 'Aalanna', 17]
    ],
    'violators_contrib': 42,
    'high_risk_obs': [
        [1, 'Work permit not filled completely / Missing required information (TBT, Location, PPE, etc)', 44],
        [2, 'Fire watch not done', 20],
        [3, 'Permit Not Closed', 11]
    ],
    'categories': [
        [1, 'Documentation & Authorizations', 61],
        [2, 'Fire Safety & Hot Work', 20],
        [3, 'Work at Height', 10],
        [4, 'PPE', 4]
    ]
}

# ----------------- WORKPLAN HTML RENDER HELPERS -----------------

def render_planned_assessed_donut():
    # 92% Assessed, 8% Gap
    fig = go.Figure(data=[go.Pie(
        labels=['Assessed', 'Pending'],
        values=[92, 8],
        hole=.7,
        marker=dict(colors=['#10b981', '#f1f5f9']),
        textinfo='none',
        hoverinfo='label+percent'
    )])
    
    fig.update_layout(
        showlegend=False,
        annotations=[dict(
            text="<span style='font-size:22px; font-weight:800; color:#10b981; font-family:\"Danone One\", Inter, sans-serif;'>92%</span><br><span style='font-size:8px; color:#64748b; font-weight:600;'>Conducted</span>",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=10)
        )],
        margin=dict(l=0, r=0, t=0, b=0),
        height=95,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    return fig

def render_risk_pie_chart():
    labels = ['High', 'Medium', 'Low', 'Very Low']
    values = [6, 10, 14, 14]
    colors = ['#ef4444', '#f97316', '#f59e0b', '#10b981'] # Slate / Tailored Red, Orange, Yellow, Green
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=.6,
        marker=dict(colors=colors),
        textinfo='percent',
        textposition='inside',
        hoverinfo='label+value+percent'
    )])
    
    fig.update_layout(
        showlegend=False,
        annotations=[dict(
            text="<span style='font-size:10px; color:#64748b; font-family:\"Danone One\", Inter, sans-serif;'>Total Risks</span><br><span style='font-size:16px; font-weight:800; color:#002256;'>44</span>",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=14)
        )],
        margin=dict(l=0, r=0, t=0, b=0),
        height=95,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    return fig

def generate_workplan_table(title, headers, rows):
    header_cols_html = "".join(f"<th style='background-color:#002256; color:white; padding:8px; border: 1px solid #e2e8f0; text-align:center; font-size:12px; font-weight:700; text-transform:uppercase;'>{h}</th>" for h in headers)
    
    rows_html = ""
    for row_idx, r in enumerate(rows):
        row_cols_html = ""
        is_total = (row_idx == len(rows) - 1)
        bg_color = "#f8fafc" if is_total else "#ffffff"
        font_weight = "bold" if is_total else "normal"
        border_top = "2px solid #002256" if is_total else "1px solid #e2e8f0"
        
        for col_idx, val in enumerate(r):
            align = "left" if col_idx == 0 else "center"
            val_str = str(val)
            if col_idx == 0:
                if "Heavy Lifting" in val_str:
                    val_str = "🏗️ " + val_str
                elif "Work at Height" in val_str:
                    val_str = "🧗 " + val_str
                elif "Civil Works" in val_str:
                    val_str = "🧱 " + val_str
            
            row_cols_html += f"<td style='padding:8px; border: 1px solid #e2e8f0; border-top: {border_top}; text-align:{align}; font-size:12.5px; font-weight:{font_weight}; color:#334155; font-family:\"Danone One\", \"Inter\", sans-serif; background-color:{bg_color};'>{val_str}</td>"
        rows_html += f"<tr>{row_cols_html}</tr>"
        
    html = f"""
    <div style='margin-bottom:20px; border-radius:8px; overflow:hidden; border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,0.05);'>
        <div style='background-color:#002256; color:white; padding:10px 12px; font-size:13px; font-weight:700; text-align:center; letter-spacing:0.5px; text-transform:uppercase; font-family:\"Danone One\", \"Inter\", sans-serif;'>
            {title}
        </div>
        <table style='width:100%; border-collapse:collapse; background-color:#ffffff;'>
            <thead>
                <tr>{header_cols_html}</tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
    </div>
    """
    return html

# ----------------- WORKPLAN STATIC DATA -----------------

STATIC_WORKPLAN = {
    'planned': 120,
    'assessed': 110,
    'gap': 10,
    'critical_controls': 396,
    'jsa_prepared': 352,
    'method_statement': 328,
    'controls_ready': 346,
    'risks': {
        'high': 6,
        'medium': 10,
        'low': 14,
        'very_low': 14,
        'total': 44
    },
    'table_data': [
        ["Heavy Lifting & Shifting", "32 (91%)", "128", "112 (88%)", "83%", "<span style='color:#fa5252; font-weight:bold;'>4 (12%)</span>"],
        ["Work at Height", "36 (90%)", "132", "116 (88%)", "82%", "<span style='color:#fa5252; font-weight:bold;'>6 (15%)</span>"],
        ["Civil Works", "42 (93%)", "136", "118 (87%)", "86%", "<span style='color:#fa5252; font-weight:bold;'>6 (13%)</span>"],
        ["TOTAL", "110 (92%)", "396", "346 (87%)", "84%", "<span style='color:#fa5252; font-weight:bold;'>16 (14%)</span>"]
    ]
}

# ----------------- SIDEBAR -----------------

st.sidebar.image(get_path("danone_logo.png"), use_container_width=True)

st.sidebar.markdown("<h3 style='text-align: center; color: white;'>📋 DASHBOARD SELECT</h3>", unsafe_allow_html=True)
active_dashboard = st.sidebar.selectbox(
    "Active Dashboard",
    ["🛡️ CSFA Dashboard", "📋 PTW Dashboard", "📅 Workplan Dashboard"],
    label_visibility="collapsed"
)
st.sidebar.markdown("<hr style='border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)

# ----------------- ROUTING -----------------

if active_dashboard == "🛡️ CSFA Dashboard":
    # ----------------- CSFA SIDEBAR CONTROLS -----------------
    config = load_config()
    current_path = config.get("csfa_path", get_path("CSFA Accumilative data.xlsx"))

    with st.sidebar.expander("📁 FILE PATH SETTINGS", expanded=False):
        excel_path_input = st.text_input("Excel Path", value=current_path, help="Path to your local synced SharePoint CSFA Accumilative data.xlsx file")
        if excel_path_input != current_path:
            if st.button("💾 Save Excel Path", use_container_width=True):
                config["csfa_path"] = excel_path_input
                save_config(config)
                st.cache_data.clear()
                st.rerun()

    st.sidebar.markdown("<hr style='border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
    st.sidebar.markdown("<h2 style='text-align: center; color: white;'>⚙️ CONTROLS</h2>", unsafe_allow_html=True)

    # Refresh Button
    if st.sidebar.button("🔄 Refresh Dashboard Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.sidebar.markdown("<hr style='border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
    st.sidebar.markdown("<h4 style='color: white;'>🔍 FILTERS</h4>", unsafe_allow_html=True)

    df_raw = load_data()
    path_exists = os.path.exists(current_path)

    # Date Picker Filter
    if not df_raw.empty:
        min_date = df_raw['Date'].min().date() if pd.notna(df_raw['Date'].min()) else datetime.now().date() - timedelta(days=90)
        max_date = df_raw['Date'].max().date() if pd.notna(df_raw['Date'].max()) else datetime.now().date()
        
        start_date = st.sidebar.date_input("Start Date", min_date, min_value=min_date, max_value=max_date)
        end_date = st.sidebar.date_input("End Date", max_date, min_value=min_date, max_value=max_date)
        
        if start_date > end_date:
            st.sidebar.error("Error: Start Date must be before or equal to End Date.")
    else:
        start_date = datetime.now().date() - timedelta(days=90)
        end_date = datetime.now().date()

    # Manpower input
    manpower = st.sidebar.number_input("Average Manpower / Day", min_value=1, value=168, step=1)

    ignore_contractors = [
        'nan', 'no one working at roof area.', 'no one working at the time of visit',
        'no one outside', 'no one was working here', 'common area', 'general', 'all',
        'no work happening here', 'test', 'spot', 'leakage', 'general observations',
        'oil storage shed', 'common for all', 'oil injection area', 'none'
    ]

    # Apply Filters
    if not df_raw.empty and start_date <= end_date:
        df_filtered = df_raw[(df_raw['Date'].dt.date >= start_date) & (df_raw['Date'].dt.date <= end_date)]
    else:
        df_filtered = pd.DataFrame()

    # ----------------- CSFA HEADER & MAIN RENDER -----------------
    if not df_filtered.empty:
        date_display_str = f"Range: {start_date.strftime('%d-%b-%Y')} to {end_date.strftime('%d-%b-%Y')}"
    else:
        date_display_str = "No data available"

    st.markdown(f"""
    <div class="dashboard-header">
        <div class="header-title-box">
            <div class="header-main-title">DAILY RISK BASED CONTRACTOR SAFETY FIELD AUDITS DASHBOARD</div>
            <div class="header-sub-title"></div>
        </div>
        <div class="header-info-box">
            <div class="header-info-lbl">Reporting Window</div>
            <div class="header-info-date">📅 {date_display_str}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not path_exists:
        st.error("⚠️ Excel file not found!")
        st.info(f"The dashboard is trying to load: `{current_path}`\n\nPlease ensure your local OneDrive/SharePoint sync folder path is correct and configure it in the sidebar.")
    elif df_filtered.empty:
        st.warning("⚠️ No safety observation data found for the selected date range. Please choose a broader window in the sidebar.")
    else:
        # CSFA CALCULATIONS
        df_valid_contractors = df_filtered[~df_filtered['Contractor name'].str.lower().str.strip().isin(ignore_contractors)]
        total_contractors = df_valid_contractors['Contractor name'].nunique()
        avg_severity = df_filtered['Severity'].mean()
        
        high_sev_df = df_filtered[df_filtered['Severity'].isin([4, 5])]
        total_high_sev = len(high_sev_df)
        
        unique_audit_days = df_filtered['Date'].dt.date.nunique()
        high_sev_per_day = (total_high_sev / unique_audit_days) if unique_audit_days > 0 else 0.0
        
        closed_high_sev = len(high_sev_df[high_sev_df['Status'].str.lower() == 'closed'])
        high_sev_closure = (closed_high_sev / total_high_sev * 100) if total_high_sev > 0 else 0.0
        
        unsafe_acts = df_filtered['unsafe acts'].sum()
        unsafe_cond = df_filtered['unsafe Condes'].sum()
        unsafe_ratio = (unsafe_acts / unsafe_cond) if unsafe_cond > 0 else 0.0

        # Aligned KPI Row (HTML/CSS Flexbox)
        st.markdown(f"""
        <div style="display: flex; gap: 15px; margin-bottom: 25px; align-items: stretch; width: 100%; flex-wrap: wrap; font-family: 'Danone One', 'Inter', -apple-system, sans-serif;">
            <!-- Card 1 -->
            <div style="flex: 1; min-width: 200px; background-color: #ffffff; border-radius: 8px; padding: 18px; border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,0.05); display: flex; flex-direction: column; justify-content: space-between; height: 120px;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; width: 100%;">
                    <span style="font-size: 11px; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px;">Total No. of Contractors</span>
                    <span style="font-size: 14px; background-color: #f8fafc; width: 26px; height: 26px; border-radius: 6px; display: flex; align-items: center; justify-content: center; border: 1px solid #e2e8f0; box-shadow: 0 1px 2px rgba(0,0,0,0.02);">👥</span>
                </div>
                <div style="font-size: 26px; font-weight: 800; color: #0033a0; line-height: 1.1; letter-spacing: -0.5px; margin-top: 8px;">{total_contractors}</div>
            </div>
            <!-- Card 2 -->
            <div style="flex: 1; min-width: 200px; background-color: #ffffff; border-radius: 8px; padding: 18px; border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,0.05); display: flex; flex-direction: column; justify-content: space-between; height: 120px;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; width: 100%;">
                    <span style="font-size: 11px; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px;">Average Manpower / Day</span>
                    <span style="font-size: 14px; background-color: #f8fafc; width: 26px; height: 26px; border-radius: 6px; display: flex; align-items: center; justify-content: center; border: 1px solid #e2e8f0; box-shadow: 0 1px 2px rgba(0,0,0,0.02);">👷</span>
                </div>
                <div style="font-size: 26px; font-weight: 800; color: #0033a0; line-height: 1.1; letter-spacing: -0.5px; margin-top: 8px;">{manpower}</div>
            </div>
            <!-- Card 3 -->
            <div style="flex: 1; min-width: 200px; background-color: #ffffff; border-radius: 8px; padding: 18px; border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,0.05); display: flex; flex-direction: column; justify-content: space-between; height: 120px;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; width: 100%;">
                    <span style="font-size: 11px; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px;">Site Severity Score</span>
                    <span style="font-size: 14px; background-color: #f8fafc; width: 26px; height: 26px; border-radius: 6px; display: flex; align-items: center; justify-content: center; border: 1px solid #e2e8f0; box-shadow: 0 1px 2px rgba(0,0,0,0.02);">🛡️</span>
                </div>
                <div style="font-size: 26px; font-weight: 800; color: #0033a0; line-height: 1.1; letter-spacing: -0.5px; margin-top: 8px;">{avg_severity:.1f}</div>
            </div>
            <!-- High Severity Stat Block -->
            <div style="flex: 2; min-width: 400px; background-color: #fff8f8; border-radius: 8px; padding: 18px; border: 1px solid #fee2e2; box-shadow: 0 1px 3px rgba(0,0,0,0.05); display: flex; flex-direction: column; justify-content: space-between; height: 120px;">
                <div style="font-size: 11px; font-weight: 800; color: #ef4444; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;">🚨 High Severity Observations (Severity 4 & 5)</div>
                <div style="display: flex; justify-content: space-between; align-items: center; width: 100%; margin-top: 4px;">
                    <div>
                        <div style="font-size: 9px; font-weight: 600; color: #991b1b; text-transform: uppercase; letter-spacing: 0.5px;">Total Obs</div>
                        <div style="font-size: 22px; font-weight: 800; color: #ef4444; margin-top: 2px;">{total_high_sev}</div>
                    </div>
                    <div style="width: 1px; height: 30px; background-color: #fca5a5;"></div>
                    <div>
                        <div style="font-size: 9px; font-weight: 600; color: #991b1b; text-transform: uppercase; letter-spacing: 0.5px;">Obs / Day</div>
                        <div style="font-size: 22px; font-weight: 800; color: #ef4444; margin-top: 2px;">{high_sev_per_day:.1f}</div>
                    </div>
                    <div style="width: 1px; height: 30px; background-color: #fca5a5;"></div>
                    <div>
                        <div style="font-size: 9px; font-weight: 600; color: #991b1b; text-transform: uppercase; letter-spacing: 0.5px;">Closure Rate</div>
                        <div style="font-size: 22px; font-weight: 800; color: #22c55e; margin-top: 2px;">{high_sev_closure:.0f}%</div>
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # CSFA Visualizations
        row1_c1, row1_c2, row1_c3 = st.columns([1, 1, 1.2])
        
        with row1_c1:
            with st.container(border=True):
                st.markdown("<h4 style='margin:0; padding-bottom:8px; border-bottom:2px solid #0033a0; color:#002060; font-weight:800; font-size:14px; text-transform:uppercase;'>📊 TOP OBSERVATION CATEGORIES</h4>", unsafe_allow_html=True)
                df_trends = df_filtered[df_filtered['Trend'].notna() & (df_filtered['Trend'] != "") & (df_filtered['Trend'].str.lower() != "nan")]
                if not df_trends.empty:
                    trend_counts = df_trends['Trend'].value_counts().reset_index()
                    trend_counts.columns = ['Category', 'Count']
                    trend_counts = trend_counts.sort_values('Count', ascending=True)
                    
                    fig_trends = px.bar(
                        trend_counts.tail(8),
                        x='Count',
                        y='Category',
                        orientation='h',
                        color_discrete_sequence=['#0055b8'],
                        text='Count'
                    )
                    fig_trends.update_layout(
                        margin=dict(l=10, r=10, t=10, b=10),
                        height=240,
                        xaxis_title="",
                        yaxis_title="",
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font=dict(family="Inter, sans-serif"),
                        xaxis=dict(showgrid=True, gridcolor="#f1f5f9"),
                        yaxis=dict(showgrid=False)
                    )
                    st.plotly_chart(fig_trends, use_container_width=True, config={'displayModeBar': False})
                else:
                    st.markdown("<div style='height:240px; display:flex; align-items:center; justify-content:center; color:#64748b; font-size:14px;'>No classified Trend data in this date range.</div>", unsafe_allow_html=True)
                
        with row1_c2:
            with st.container(border=True):
                st.markdown("<h4 style='margin:0; padding-bottom:8px; border-bottom:2px solid #0033a0; color:#002060; font-weight:800; font-size:14px; text-transform:uppercase;'>🎯 ACTION / CONDITION RATIO</h4>", unsafe_allow_html=True)
                fig_gauge = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = unsafe_ratio,
                    domain = {'x': [0, 1], 'y': [0, 1]},
                    gauge = {
                        'axis': {'range': [0, 1.5], 'tickwidth': 1, 'tickcolor': "#002256"},
                        'bar': {'color': "#002256"},
                        'steps': [
                            {'range': [0, 0.4], 'color': "#e2f0d9"},
                            {'range': [0.4, 0.8], 'color': "#fff2cc"},
                            {'range': [0.8, 1.5], 'color': "#fce4d6"}
                        ],
                        'threshold': {
                            'line': {'color': "#ef4444", 'width': 4},
                            'thickness': 0.75,
                            'value': unsafe_ratio
                        }
                    }
                ))
                fig_gauge.update_layout(
                    margin=dict(l=20, r=20, t=15, b=10),
                    height=210,
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(family="Inter, sans-serif")
                )
                st.plotly_chart(fig_gauge, use_container_width=True, config={'displayModeBar': False})
                st.markdown(f"<div style='text-align:center; font-size:12px; color:#64748b; font-weight:600; font-family:Inter, sans-serif;'>Acts: <b>{unsafe_acts}</b> &nbsp;|&nbsp; Conditions: <b>{unsafe_cond}</b></div>", unsafe_allow_html=True)
            
        with row1_c3:
            with st.container(border=True):
                st.markdown("<h4 style='margin:0; padding-bottom:8px; border-bottom:2px solid #0033a0; color:#002060; font-weight:800; font-size:14px; text-transform:uppercase;'>📍 ZONE WISE AVERAGE SEVERITY</h4>", unsafe_allow_html=True)
                df_zones = df_filtered[df_filtered['Zone'].notna() & (df_filtered['Zone'] != "") & (df_filtered['Zone'].str.lower() != "nan")]
                if not df_zones.empty:
                    zone_severity = df_zones.groupby('Zone')['Severity'].mean().reset_index()
                    zone_severity.columns = ['Zone', 'Avg Severity']
                    zone_severity = zone_severity.sort_values('Avg Severity', ascending=True)
                    
                    colors = []
                    for val in zone_severity['Avg Severity']:
                        if val >= 3.0:
                            colors.append('#d93838')
                        elif val >= 2.5:
                            colors.append('#f5a623')
                        else:
                            colors.append('#27ae60')
                    
                    fig_zones = px.bar(
                        zone_severity,
                        x='Avg Severity',
                        y='Zone',
                        orientation='h',
                        text=zone_severity['Avg Severity'].apply(lambda x: f"{x:.1f}")
                    )
                    fig_zones.update_traces(marker_color=colors)
                    fig_zones.update_layout(
                        margin=dict(l=10, r=10, t=10, b=10),
                        height=240,
                        xaxis_title="",
                        yaxis_title="",
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font=dict(family="Inter, sans-serif"),
                        xaxis=dict(showgrid=True, gridcolor="#f1f5f9"),
                        yaxis=dict(showgrid=False)
                    )
                    st.plotly_chart(fig_zones, use_container_width=True, config={'displayModeBar': False})
                else:
                    st.markdown("<div style='height:240px; display:flex; align-items:center; justify-content:center; color:#64748b; font-size:14px;'>No Zone data in this date range.</div>", unsafe_allow_html=True)

        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        row2_c1, row2_c2 = st.columns([1.2, 1])
        
        with row2_c1:
            with st.container(border=True):
                st.markdown("<h4 style='margin:0; padding-bottom:8px; border-bottom:2px solid #0033a0; color:#002060; font-weight:800; font-size:14px; text-transform:uppercase;'>🏗️ Contractor Wise Average Severity Score</h4>", unsafe_allow_html=True)
                if not df_valid_contractors.empty:
                    contractor_severity = df_valid_contractors.groupby('Contractor name')['Severity'].mean().reset_index()
                    contractor_severity.columns = ['Contractor', 'Avg Severity']
                    contractor_severity = contractor_severity.sort_values('Avg Severity', ascending=True)
                    
                    colors_contractors = []
                    for val in contractor_severity['Avg Severity']:
                        if val >= 3.0:
                            colors_contractors.append('#d93838')
                        elif val >= 2.5:
                            colors_contractors.append('#f5a623')
                        else:
                            colors_contractors.append('#27ae60')
                            
                    fig_contractors = px.bar(
                        contractor_severity,
                        x='Avg Severity',
                        y='Contractor',
                        orientation='h',
                        text=contractor_severity['Avg Severity'].apply(lambda x: f"{x:.1f}")
                    )
                    fig_contractors.update_traces(marker_color=colors_contractors)
                    fig_contractors.update_layout(
                        margin=dict(l=10, r=10, t=10, b=10),
                        height=300,
                        xaxis_title="",
                        yaxis_title="",
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font=dict(family="Inter, sans-serif"),
                        xaxis=dict(showgrid=True, gridcolor="#f1f5f9"),
                        yaxis=dict(showgrid=False)
                    )
                    st.plotly_chart(fig_contractors, use_container_width=True, config={'displayModeBar': False})
                else:
                    st.markdown("<div style='height:300px; display:flex; align-items:center; justify-content:center; color:#64748b; font-size:14px;'>No contractor observations in this date range.</div>", unsafe_allow_html=True)
                
        with row2_c2:
            with st.container(border=True):
                st.markdown("<h4 style='margin:0; padding-bottom:8px; border-bottom:2px solid #0033a0; color:#002060; font-weight:800; font-size:14px; text-transform:uppercase;'>📈 High Severity Trend (Selected vs Prior Period)</h4>", unsafe_allow_html=True)
                
                period_days = (end_date - start_date).days
                prior_end = start_date - timedelta(days=1)
                prior_start = prior_end - timedelta(days=period_days)
                
                curr_high = df_valid_contractors[df_valid_contractors['Severity'].isin([4, 5])]
                curr_counts = curr_high['Contractor name'].value_counts().reset_index()
                curr_counts.columns = ['Contractor', 'Current Period']
                
                df_prior = df_raw[(df_raw['Date'].dt.date >= prior_start) & (df_raw['Date'].dt.date <= prior_end)]
                prior_valid_contractors = df_prior[~df_prior['Contractor name'].str.lower().str.strip().isin(ignore_contractors)]
                prior_high = prior_valid_contractors[prior_valid_contractors['Severity'].isin([4, 5])]
                prior_counts = prior_high['Contractor name'].value_counts().reset_index()
                prior_counts.columns = ['Contractor', 'Prior Period']
                
                merged_trend = pd.merge(curr_counts, prior_counts, on='Contractor', how='outer').fillna(0)
                merged_trend['Current Period'] = merged_trend['Current Period'].astype(int)
                merged_trend['Prior Period'] = merged_trend['Prior Period'].astype(int)
                merged_trend['Diff'] = merged_trend['Current Period'] - merged_trend['Prior Period']
                
                merged_trend = merged_trend.sort_values('Current Period', ascending=False)
                
                trend_rows = []
                for idx, r in merged_trend.iterrows():
                    diff_val = r['Diff']
                    if diff_val > 0:
                        diff_str = f"🔺 +{diff_val}"
                    elif diff_val < 0:
                        diff_str = f"🔻 {diff_val}"
                    else:
                        diff_str = f"➖ 0"
                        
                    trend_rows.append({
                        "Contractor": r['Contractor'],
                        "High Severity Obs (Current)": r['Current Period'],
                        "Change from Prior": diff_str
                    })
                    
                if trend_rows:
                    st.dataframe(pd.DataFrame(trend_rows), hide_index=True, use_container_width=True, height=160)
                else:
                    st.markdown("<div style='height:160px; display:flex; align-items:center; justify-content:center; color:#7f8c8d; font-size:14px;'>No high severity observations found in either period.</div>", unsafe_allow_html=True)
                    
                st.markdown("""
                <div style="font-size: 11px; color: #5a6b82; border-top: 1px solid #f1f3f5; padding-top: 8px; margin-top: 8px;">
                    <b>Action Items:</b><br/>
                    • 🔍 Conduct immediate reviews and discussions with high-risk contractor owners.<br/>
                    • 🗓️ Hold daily/weekly on-ground review meetings to check and correct conditions.
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("<h4 style='margin:0; padding-bottom:8px; border-bottom:2px solid #0033a0; color:#002060; font-weight:800; font-size:14px; text-transform:uppercase;'>📋 Pending Tasks & Data Quality Sync Helper</h4>", unsafe_allow_html=True)
            
            df_missing_trend = df_raw[df_raw['Trend'].isna() | (df_raw['Trend'] == "") | (df_raw['Trend'].str.lower() == "nan")].copy()
            
            if not df_missing_trend.empty:
                st.warning(f"⚠️ There are {len(df_missing_trend)} observations in the Excel sheet that are missing a Trend classification. Please classify them in the Excel sheet.")
                df_missing_display = df_missing_trend[['ln', 'Date', 'Contractor name', 'Observation Discription ', 'Severity ']].copy()
                df_missing_display['Date'] = df_missing_display['Date'].dt.strftime('%d-%b-%Y')
                df_missing_display.columns = ['Row # (ln)', 'Date', 'Contractor', 'Observation Description', 'Severity']
                
                st.dataframe(df_missing_display.head(15), hide_index=True, use_container_width=True)
                st.caption("ℹ️ Only showing the first 15 records. Please assign a category (e.g. PPE, Work at Height, Housekeeping, Electrical, etc.) in Column B of the Excel sheet.")
            else:
                st.success("✅ All sync observations have been classified! Excellent data quality.")

elif active_dashboard == "📋 PTW Dashboard":
    # ----------------- PTW SIDEBAR CONTROLS -----------------
    config = load_config()
    current_ptw_path = config.get("ptw_path", get_ptw_path("PTW.xlsx"))
    current_ptw_audit_path = config.get("ptw_audit_path", get_ptw_path("PTW Audit.xlsx"))

    with st.sidebar.expander("📁 FILE PATH SETTINGS", expanded=False):
        ptw_path_input = st.text_input("PTW Excel Path", value=current_ptw_path, help="Path to your local PTW.xlsx file")
        ptw_audit_path_input = st.text_input("PTW Audit Excel Path", value=current_ptw_audit_path, help="Path to your local PTW Audit.xlsx file")
        if (ptw_path_input != current_ptw_path or ptw_audit_path_input != current_ptw_audit_path):
            if st.button("💾 Save PTW Settings", use_container_width=True):
                config["ptw_path"] = ptw_path_input
                config["ptw_audit_path"] = ptw_audit_path_input
                save_config(config)
                st.cache_data.clear()
                st.rerun()

    st.sidebar.markdown("<hr style='border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
    st.sidebar.markdown("<h2 style='text-align: center; color: white;'>⚙️ CONTROLS</h2>", unsafe_allow_html=True)

    if st.sidebar.button("🔄 Refresh PTW Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    # ----------------- PTW MAIN RENDER -----------------
    ptw_exists = os.path.exists(current_ptw_path)
    audit_exists = os.path.exists(current_ptw_audit_path)
    
    if ptw_exists and audit_exists:
        try:
            df_ptw_temp = pd.read_excel(current_ptw_path)
            st.sidebar.success(f"✅ Excel Connected!\nParsed PTW.xlsx ({len(df_ptw_temp)} entries)")
        except Exception as e:
            st.sidebar.warning(f"⚠️ Could not parse Excel: {e}")
    else:
        st.sidebar.warning("⚠️ Excel Files Not Connected!")

    date_display_str = "Q2 FY26"
        
    st.markdown(f"""
    <div class="dashboard-header">
        <div class="header-title-box">
            <div class="header-main-title">WORK PERMIT DASHBOARD - (ACTIONS ON HIGH-RISK CONTRACTORS & IMPROVING AUDIT COMPLIANCE)</div>
            <div class="header-sub-title"></div>
        </div>
        <div class="header-info-box">
            <div class="header-info-lbl">Reporting Window</div>
            <div class="header-info-date">📅 {date_display_str}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Static Representational Data mode
    total_issued = STATIC_PTW['total_issued']
    total_closed = STATIC_PTW['total_closed']
    total_audited = STATIC_PTW['total_audited']
    total_observations = STATIC_PTW['total_observations']
    critical_observations = STATIC_PTW['critical_observations']
    compliance = STATIC_PTW['compliance']
    compliance_donut = STATIC_PTW['compliance_donut']
    high_risk_issued = STATIC_PTW['high_risk_issued']
    high_risk_safely_executed = STATIC_PTW['high_risk_safely_executed']
    high_risk_observations = STATIC_PTW['high_risk_observations']
    violators_list = STATIC_PTW['violators']
    violators_contrib = STATIC_PTW['violators_contrib']
    high_risk_obs_list = STATIC_PTW['high_risk_obs']
    categories_list = STATIC_PTW['categories']
    
    # Render Row 1 general KPI Cards (using columns with st.container(border=True))
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        with st.container(border=True):
            render_kpi_metric("No. Of work permits issued", "📋", f"{total_issued:,}", "#0033a0")
    with col2:
        with st.container(border=True):
            render_kpi_metric("No. Of work permits closed", "✅", f"{total_closed:,}", "#27ae60")
    with col3:
        with st.container(border=True):
            render_kpi_metric("No. Of Work permits Audited", "🔍", f"{total_audited:,}", "#8e24aa")
    with col4:
        with st.container(border=True):
            render_kpi_metric("No. Of observations", "💬", f"{total_observations:,}", "#e67e22")
    with col5:
        with st.container(border=True):
            render_kpi_metric("Critical Observations", "⚠️", f"{critical_observations:,}", "#fa5252")
    with col6:
        with st.container(border=True):
            render_kpi_metric("Compliance", "📊", f"{compliance:.0f}%", "#10b981")
            
    # Render Row 2 high risk KPI Cards (using same 6 column layout but leaving last 3 empty to align)
    row2_col1, row2_col2, row2_col3, _, _, _ = st.columns(6)
    with row2_col1:
        with st.container(border=True):
            render_kpi_metric("No. of high Risk permits issued", "👷", f"{high_risk_issued:,}", "#0f766e")
    with row2_col2:
        with st.container(border=True):
            render_kpi_metric("High Risk permits Safely Executed", "✅", f"{high_risk_safely_executed:,}", "#27ae60")
    with row2_col3:
        with st.container(border=True):
            render_kpi_metric("No. Of Observations in High-Risk permits", "❗", f"{high_risk_observations:,}", "#e11d48")
            
    # Layout: Left column & Right column
    left_col, right_col = st.columns([1, 1.2])
    
    with left_col:
        # Compliance donut card
        with st.container(border=True):
            st.markdown("<h4 style='margin:0; padding-bottom:8px; border-bottom:2px solid #002060; color:#002060; font-weight:800; font-size:14px; text-transform:uppercase;'>🎯 COMPLIANCE</h4>", unsafe_allow_html=True)
            
            c_col1, c_col2 = st.columns([1, 1])
            with c_col1:
                fig_donut = render_donut_chart(compliance_donut)
                st.plotly_chart(fig_donut, use_container_width=True, config={'displayModeBar': False})
            with c_col2:
                formula_html = f"""
                <div style="display: flex; flex-direction: column; justify-content: center; height: 100%; padding-left: 10px; font-family: 'Outfit', sans-serif; height: 180px;">
                    <div style="font-size: 11.5px; color: #5a6b82; margin-bottom: 8px; font-weight: 600;">Compliance is calculated as:</div>
                    <div style="display: flex; align-items: center; font-size: 13.5px; font-weight: bold; color: #0f2c59;">
                        <div style="display: flex; flex-direction: column; align-items: center; margin-right: 8px;">
                            <div style="border-bottom: 2px solid #0f2c59; padding-bottom: 4px; text-align: center; width: 100%;">
                                {total_issued} - {total_observations}
                            </div>
                            <div style="padding-top: 4px; text-align: center; width: 100%;">
                                {total_issued}
                            </div>
                        </div>
                        <div style="font-size: 15px; font-weight: 800; margin-left: 5px;">× 100</div>
                    </div>
                </div>
                """
                st.markdown(formula_html, unsafe_allow_html=True)
        
        # Top Violators table
        violator_title = f"TOP 3 VIOLATORS – CONTRIBUTING {violators_contrib}%"
        violators_html = generate_html_table(
            violator_title,
            ["#", "CONTRACTOR", "NO. OF OBSERVATIONS"],
            violators_list
        )
        st.markdown(violators_html, unsafe_allow_html=True)
        
    with right_col:
        # Top High Risk Observations table
        hr_obs_html = generate_html_table(
            "TOP 3 HIGH RISK OBSERVATIONS",
            ["#", "OBSERVATION", "NO. OF OCCURRENCES"],
            high_risk_obs_list
        )
        st.markdown(hr_obs_html, unsafe_allow_html=True)
        
        # Categories of Violation table
        categories_html = generate_html_table(
            "CATEGORIES OF VIOLATION",
            ["#", "CATEGORY", "NO. OF OBSERVATIONS"],
            categories_list
        )
        st.markdown(categories_html, unsafe_allow_html=True)

else: # active_dashboard == "📅 Workplan Dashboard"
    # ----------------- WORKPLAN SIDEBAR CONTROLS -----------------
    config = load_config()
    current_workplan_path = config.get("workplan_path", get_workplan_path("Himalaya Work Plan - Contractor Wise.xlsx"))

    with st.sidebar.expander("📁 FILE PATH SETTINGS", expanded=False):
        workplan_path_input = st.text_input("Workplan Excel Path", value=current_workplan_path, help="Path to your local Himalaya Work Plan - Contractor Wise.xlsx file")
        if workplan_path_input != current_workplan_path:
            if st.button("💾 Save Workplan Settings", use_container_width=True):
                config["workplan_path"] = workplan_path_input
                save_config(config)
                st.cache_data.clear()
                st.rerun()

    st.sidebar.markdown("<hr style='border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
    st.sidebar.markdown("<h2 style='text-align: center; color: white;'>⚙️ CONTROLS</h2>", unsafe_allow_html=True)

    if st.sidebar.button("🔄 Refresh Workplan Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    # ----------------- WORKPLAN MAIN RENDER -----------------
    workplan_exists = os.path.exists(current_workplan_path)
    
    if workplan_exists:
        try:
            xl = pd.ExcelFile(current_workplan_path)
            sheets_count = len(xl.sheet_names)
            total_rows = 0
            for sheet in xl.sheet_names:
                if sheet not in ['Guidelines', 'Sheet1']:
                    df_temp = xl.parse(sheet)
                    total_rows += len(df_temp)
            st.sidebar.success(f"✅ Excel Connected!\nParsed {sheets_count} sheets ({total_rows} entries)")
        except Exception as e:
            st.sidebar.warning(f"⚠️ Could not parse Excel: {e}")
    else:
        st.sidebar.warning("⚠️ Excel File Not Connected!")

    date_display_str = "Q2 FY26"
    
    st.markdown(f"""
    <div class="dashboard-header">
        <div class="header-title-box">
            <div class="header-main-title">HIGH RISK ACTIVITIES – RISK MANAGEMENT OVERVIEW</div>
            <div class="header-sub-title"></div>
        </div>
        <div class="header-info-box">
            <div class="header-info-lbl">Reporting Window</div>
            <div class="header-info-date">📅 Period: {date_display_str}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Static Representational Data mode
    planned = STATIC_WORKPLAN['planned']
    assessed = STATIC_WORKPLAN['assessed']
    gap = STATIC_WORKPLAN['gap']
    critical_controls = STATIC_WORKPLAN['critical_controls']
    jsa_prepared = STATIC_WORKPLAN['jsa_prepared']
    method_statement = STATIC_WORKPLAN['method_statement']
    controls_ready = STATIC_WORKPLAN['controls_ready']
    table_data = STATIC_WORKPLAN['table_data']
    
    # First row: Planned vs Assessed + KPI Cards + Risk Chart
    col1, col2, col3, col4, col5, col6 = st.columns([1.3, 1, 1, 1, 1, 1.3])
    
    with col1:
        with st.container(border=True):
            st.markdown("<div style='font-size:9.5px; font-weight:bold; color:#5a6b82; text-transform:uppercase; text-align:center; height:28px; display:flex; align-items:center; justify-content:center; line-height:1.2; margin-bottom:4px;'>Planned vs Risk Assessment</div>", unsafe_allow_html=True)
            sub_c1, sub_c2 = st.columns([1, 1.1])
            with sub_c1:
                fig_planned = render_planned_assessed_donut()
                st.plotly_chart(fig_planned, use_container_width=True, config={'displayModeBar': False})
            with sub_c2:
                st.markdown(f"""
                <div style="font-family:'Outfit', sans-serif; font-size:11px; color:#333; margin-top:15px; display:flex; flex-direction:column; gap:6px;">
                    <div style="display:flex; align-items:center;">
                        <div style="width:8px; height:8px; background-color:#0033a0; margin-right:6px; border-radius:1.5px;"></div>
                        Planned: <b>{planned}</b>
                    </div>
                    <div style="display:flex; align-items:center;">
                        <div style="width:8px; height:8px; background-color:#27ae60; margin-right:6px; border-radius:1.5px;"></div>
                        Assessed: <b>{assessed}</b>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            st.markdown(f"<div style='font-size:9px; color:#7f8c8d; text-align:center; border-top:1px solid #f1f3f5; padding-top:4px; margin-top:4px; font-weight:600;'>Gap: {gap} pending assessment</div>", unsafe_allow_html=True)
            
    with col2:
        with st.container(border=True):
            render_kpi_metric("No. of Critical Controls Identified", "📋", str(critical_controls), "#0033a0", "▲ +12% vs Apr 24")
        
    with col3:
        with st.container(border=True):
            render_kpi_metric("No. of JSA Prepared", "📄", str(jsa_prepared), "#e0a106", "▲ +10% vs Apr 24")
        
    with col4:
        with st.container(border=True):
            render_kpi_metric("No. of Method Statement Prepared", "📝", str(method_statement), "#8e24aa", "▲ +11% vs Apr 24")
        
    with col5:
        with st.container(border=True):
            render_kpi_metric("No. of Critical Controls Ready for Execution", "🛡️", str(controls_ready), "#27ae60", "▲ +87% of Identified")
        
    with col6:
        with st.container(border=True):
            st.markdown("<div style='font-size:9.5px; font-weight:bold; color:#5a6b82; text-transform:uppercase; text-align:center; height:28px; display:flex; align-items:center; justify-content:center; line-height:1.2; margin-bottom:4px;'>Risk in Executions</div>", unsafe_allow_html=True)
            fig_risk = render_risk_pie_chart()
            st.plotly_chart(fig_risk, use_container_width=True, config={'displayModeBar': False})
            
    # Layout: Left column & Right column
    left_col, right_col = st.columns([1.3, 1])
    
    with left_col:
        # Reference Data table
        table_html = generate_workplan_table(
            "REFERENCE DATA – BY CRITICAL ACTIVITY",
            ["CRITICAL ACTIVITY", "ASSESSMENTS COMPLETED", "CRITICAL CONTROLS IDENTIFIED", "CRITICAL CONTROLS READY FOR EXECUTION", "COMPLIANCE FOR EXECUTION", "HIGH RISKS IN EXECUTION"],
            table_data
        )
        st.markdown(table_html, unsafe_allow_html=True)
        
    with right_col:
        # Key Insights card
        insights_html = """
        <div style='background-color:white; border-radius:8px; border: 1px solid #dee2e6; box-shadow: 0 4px 10px rgba(0,0,0,0.03); margin-bottom:20px; overflow:hidden;'>
            <div style='background-color:#0f2c59; color:white; padding:10px 12px; font-size:13px; font-weight:800; text-align:center; letter-spacing:0.5px; text-transform:uppercase; font-family:"Outfit", sans-serif;'>
                Key Insights
            </div>
            <div style='padding:15px; font-family:"Outfit", sans-serif; font-size:12.5px; line-height:1.6; color:#333;'>
                <div style='display:flex; align-items:flex-start; margin-bottom:10px;'>
                    <span style='margin-right:10px; font-size:16px; color:#27ae60;'>✔️</span>
                    <span><b>92%</b> of planned <span style='text-decoration:underline;'>high risk</span> activities have been assessed.</span>
                </div>
                <div style='display:flex; align-items:flex-start; margin-bottom:10px;'>
                    <span style='margin-right:10px; font-size:16px; color:#27ae60;'>📈</span>
                    <span><b>87%</b> of critical controls are ready for execution.</span>
                </div>
                <div style='display:flex; align-items:flex-start; margin-bottom:10px;'>
                    <span style='margin-right:10px; font-size:16px; color:#27ae60;'>🛡️</span>
                    <span>Compliance for execution improved to <b>84%</b>.</span>
                </div>
                <div style='display:flex; align-items:flex-start; margin-bottom:10px;'>
                    <span style='margin-right:10px; font-size:16px; color:#fa5252;'>⚠️</span>
                    <span style='color:#fa5252; font-weight:bold;'>16 high risks (14%) remain in execution – immediate focus required.</span>
                </div>
                <div style='display:flex; align-items:flex-start;'>
                    <span style='margin-right:10px; font-size:16px; color:#0033a0;'>👥</span>
                    <span>Continue to strengthen controls and ensure compliance in the field.</span>
                </div>
            </div>
        </div>
        """
        st.markdown(insights_html, unsafe_allow_html=True)
        
        # Top 3 Risks card
        risks_html = """
        <div style='background-color:white; border-radius:8px; border: 1px solid #dee2e6; box-shadow: 0 4px 10px rgba(0,0,0,0.03); overflow:hidden;'>
            <div style='background-color:#0f2c59; color:white; padding:10px 12px; font-size:13px; font-weight:800; text-align:center; letter-spacing:0.5px; text-transform:uppercase; font-family:"Outfit", sans-serif;'>
                Top 3 Risks in Executions
            </div>
            <div style='padding:15px; font-family:"Outfit", sans-serif; font-size:12.5px; color:#333;'>
                <div style='display:flex; align-items:center; margin-bottom:10px; border-bottom:1px solid #f1f3f5; padding-bottom:6px;'>
                    <div style='background-color:#e03131; color:white; border-radius:50%; width:22px; height:22px; display:flex; align-items:center; justify-content:center; font-weight:bold; margin-right:10px; font-size:11px;'>1</div>
                    <span style='font-size:18px; margin-right:10px;'>🧗</span>
                    <div style='flex-grow:1;'>
                        <div style='font-weight:bold; color:#0f2c59; font-size:11.5px; text-transform:uppercase; line-height:1.2;'>Fall From Height</div>
                        <div style='font-size:10.5px; color:#7f8c8d;'>7 Risks (44%)</div>
                    </div>
                </div>
                <div style='display:flex; align-items:center; margin-bottom:10px; border-bottom:1px solid #f1f3f5; padding-bottom:6px;'>
                    <div style='background-color:#f76707; color:white; border-radius:50%; width:22px; height:22px; display:flex; align-items:center; justify-content:center; font-weight:bold; margin-right:10px; font-size:11px;'>2</div>
                    <span style='font-size:18px; margin-right:10px;'>🏗️</span>
                    <div style='flex-grow:1;'>
                        <div style='font-weight:bold; color:#0f2c59; font-size:11.5px; text-transform:uppercase; line-height:1.2;'>Load Handling / Lifting</div>
                        <div style='font-size:10.5px; color:#7f8c8d;'>5 Risks (31%)</div>
                    </div>
                </div>
                <div style='display:flex; align-items:center; margin-bottom:10px;'>
                    <div style='background-color:#fab005; color:white; border-radius:50%; width:22px; height:22px; display:flex; align-items:center; justify-content:center; font-weight:bold; margin-right:10px; font-size:11px;'>3</div>
                    <span style='font-size:18px; margin-right:10px;'>🚜</span>
                    <div style='flex-grow:1;'>
                        <div style='font-weight:bold; color:#0f2c59; font-size:11.5px; text-transform:uppercase; line-height:1.2;'>Struck by Moving Objects</div>
                        <div style='font-size:10.5px; color:#7f8c8d;'>4 Risks (25%)</div>
                    </div>
                </div>
                <div style='background-color:#fff5f5; border:1px solid #ffe3e3; border-radius:6px; padding:8px 10px; text-align:center; margin-top:12px; font-weight:bold; color:#e03131; font-size:12.5px;'>
                    Total High Risks in Execution: 16 (14%)
                </div>
            </div>
        </div>
        """
        st.markdown(risks_html, unsafe_allow_html=True)
