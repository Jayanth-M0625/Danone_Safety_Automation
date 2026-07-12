import os
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go

from config.dashboard_config import DEFAULT_CSFA_PATH, S3_CACHE_DIR, load_config, save_config
from utils.data_loaders import load_csfa_data
from dashboards import render_source_selector

# ── Category Icon Mapper ──────────────────────────────────────────────────────
category_icons = {
    "material management": "📦 Material Management",
    "ppe": "🦺 PPE",
    "work at height": "🧗 Work at Height",
    "electrical": "⚡ Electrical",
    "barricading": "🚧 Barricading",
    "housekeeping": "🧹 Housekeeping",
    "access & egress": "🚪 Access & Egress",
    "lifting operations": "🏗️ Lifting Operations",
}

def get_category_label(cat_name):
    cat_lower = str(cat_name).lower().strip()
    for key, label in category_icons.items():
        if key in cat_lower:
            return label
    return f"🛡️ {cat_name}"

def get_severity_color(val):
    if val >= 3.5:
        return '#d93838'  # Solid Red
    elif val >= 3.0:
        return '#e05656'  # Light Red
    elif val >= 2.5:
        return '#f5a623'  # Orange
    elif val >= 2.0:
        return '#eab308'  # Yellow/Gold
    else:
        return '#27ae60'  # Green

def render_html(html_str):
    """Renders HTML directly to Streamlit, bypassing markdown parsing completely to avoid code block issues."""
    st.html(html_str)

# ── Main Render ───────────────────────────────────────────────────────────────
def render_csfa_dashboard():
    # Render Data Source Selector in Sidebar (Handles dropdown local file uploader)
    source_type = render_source_selector("csfa")
    
    # Sidebar File Path Settings
    config = load_config()
    current_path = config.get("csfa_path", DEFAULT_CSFA_PATH)
    path_exists = True
    
    if source_type == "aws":
        aws_path = os.path.join(S3_CACHE_DIR, "CSFA Accumilative data.xlsx")
        df_raw = load_csfa_data(aws_path)
        path_exists = os.path.exists(aws_path)
    else:  # upload mode
        uploaded_file = st.session_state.get("csfa_file")
        if uploaded_file is not None:
            df_raw = load_csfa_data(uploaded_file)
            path_exists = True
        else:
            df_raw = pd.DataFrame()
            path_exists = False

    st.sidebar.markdown("<hr style='border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
    st.sidebar.markdown("<h2 style='text-align: center; color: white;'>⚙️ CONTROLS</h2>", unsafe_allow_html=True)

    # Refresh Button
    if st.sidebar.button("🔄 Refresh Dashboard Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.sidebar.markdown("<hr style='border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
    st.sidebar.markdown("<h4 style='color: white;'>🔍 FILTERS</h4>", unsafe_allow_html=True)

    # Date Picker Filter
    if not df_raw.empty and 'Date' in df_raw.columns:
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

    # Apply Date Filters
    if not df_raw.empty and 'Date' in df_raw.columns and start_date <= end_date:
        df_filtered = df_raw[(df_raw['Date'].dt.date >= start_date) & (df_raw['Date'].dt.date <= end_date)]
    else:
        df_filtered = pd.DataFrame()

    # CSFA Header Display
    if not df_filtered.empty:
        date_display_str = f"{start_date.strftime('%d-%b-%Y')} to {end_date.strftime('%d-%b-%Y')}"
    else:
        date_display_str = "No data available"

    header_html = f"""
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
    """
    render_html(header_html)

    # Error handling & warnings if data doesn't exist
    if source_type == "aws" and not path_exists:
        st.warning("⚠️ AWS S3 local cache not found. Please click '☁️ Sync AWS' first to download the latest files.")
        return
    elif source_type == "upload" and not path_exists:
        st.warning("⚠️ Please upload a CSFA Excel file (.xlsx) in the sidebar to visualize.")
        return
    elif df_filtered.empty:
        st.warning("⚠️ No safety observation data found for the selected date range. Please choose a broader window in the sidebar.")
        return

    # CSFA CALCULATIONS
    df_valid_contractors = df_filtered[df_filtered['Contractor name'].notna() & ~df_filtered['Contractor name'].astype(str).str.lower().str.strip().isin(ignore_contractors)]
    total_contractors = df_valid_contractors['Contractor name'].nunique() if not df_valid_contractors.empty else 0
    avg_severity = df_filtered['Severity'].mean() if 'Severity' in df_filtered.columns else 0
    
    total_high_sev = 0
    high_sev_per_day = 0.0
    high_sev_closure = 0.0
    
    if 'Severity' in df_filtered.columns:
        high_sev_df = df_filtered[df_filtered['Severity'].isin([4, 5])]
        total_high_sev = len(high_sev_df)
        unique_audit_days = df_filtered['Date'].dt.date.nunique()
        high_sev_per_day = (total_high_sev / unique_audit_days) if unique_audit_days > 0 else 0.0
        
        if 'Status' in df_filtered.columns:
            closed_high_sev = len(high_sev_df[high_sev_df['Status'].str.lower() == 'closed'])
            high_sev_closure = (closed_high_sev / total_high_sev * 100) if total_high_sev > 0 else 0.0

    unsafe_acts = df_filtered['unsafe acts'].sum() if 'unsafe acts' in df_filtered.columns else 0
    unsafe_cond = df_filtered['unsafe Condes'].sum() if 'unsafe Condes' in df_filtered.columns else 0
    unsafe_ratio = (unsafe_acts / unsafe_cond) if unsafe_cond > 0 else 0.0

    # ── Render Header KPI Cards (Optimized layout based on mockup, darker text) ────────────
    kpi_c1, kpi_c2, kpi_c3, kpi_c4 = st.columns([1.1, 1.1, 1.1, 2.2])

    with kpi_c1:
        render_html(f"""
        <div style="background-color: #ffffff; border-radius: 12px; padding: 18px; border: 1px solid #cbd5e1; box-shadow: 0 4px 12px rgba(0,34,86,0.06); display: flex; align-items: center; gap: 15px; height: 110px; position: relative;">
            <div style="background-color: #eef2ff; width: 44px; height: 44px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 20px; flex-shrink: 0; border: 1px solid #bfdbfe;">👥</div>
            <div style="flex-grow: 1; display: flex; flex-direction: column; justify-content: center;">
                <div style="font-size: 10px; font-weight: 900; color: #1e293b; text-transform: uppercase; letter-spacing: 0.5px; line-height: 1.2;">Total No. of Contractors</div>
                <div style="font-size: 28px; font-weight: 950; color: #002b80; line-height: 1; margin-top: 4px;">{total_contractors}</div>
                <div style="width: 30px; height: 3px; background-color: #0033a0; border-radius: 2px; margin-top: 6px;"></div>
            </div>
            <div style="position: absolute; right: 12px; bottom: 8px; font-size: 32px; opacity: 0.04; font-weight: 900;">👥</div>
        </div>
        """)

    with kpi_c2:
        render_html(f"""
        <div style="background-color: #ffffff; border-radius: 12px; padding: 18px; border: 1px solid #cbd5e1; box-shadow: 0 4px 12px rgba(0,34,86,0.06); display: flex; align-items: center; gap: 15px; height: 110px; position: relative;">
            <div style="background-color: #fffbeb; width: 44px; height: 44px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 20px; flex-shrink: 0; border: 1px solid #fef08a;">👷</div>
            <div style="flex-grow: 1; display: flex; flex-direction: column; justify-content: center;">
                <div style="font-size: 10px; font-weight: 900; color: #1e293b; text-transform: uppercase; letter-spacing: 0.5px; line-height: 1.2;">Average Manpower / Day</div>
                <div style="font-size: 28px; font-weight: 950; color: #001f4d; line-height: 1; margin-top: 4px;">{manpower}</div>
                <div style="width: 30px; height: 3px; background-color: #d97706; border-radius: 2px; margin-top: 6px;"></div>
            </div>
            <div style="position: absolute; right: 12px; bottom: 8px; font-size: 32px; opacity: 0.04; font-weight: 900;">👷</div>
        </div>
        """)

    with kpi_c3:
        render_html(f"""
        <div style="background-color: #ffffff; border-radius: 12px; padding: 18px; border: 1px solid #cbd5e1; box-shadow: 0 4px 12px rgba(0,34,86,0.06); display: flex; align-items: center; gap: 15px; height: 110px; position: relative;">
            <div style="background-color: #e0f2fe; width: 44px; height: 44px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 20px; flex-shrink: 0; border: 1px solid #bae6fd;">🛡️</div>
            <div style="flex-grow: 1; display: flex; flex-direction: column; justify-content: center;">
                <div style="font-size: 10px; font-weight: 900; color: #1e293b; text-transform: uppercase; letter-spacing: 0.5px; line-height: 1.2;">Site Severity Score</div>
                <div style="font-size: 28px; font-weight: 950; color: #001f4d; line-height: 1; margin-top: 4px;">{avg_severity:.1f}</div>
                <div style="width: 30px; height: 3px; background-color: #0284c7; border-radius: 2px; margin-top: 6px;"></div>
            </div>
            <div style="position: absolute; right: 12px; bottom: 8px; font-size: 32px; opacity: 0.04; font-weight: 900;">🛡️</div>
        </div>
        """)

    with kpi_c4:
        render_html(f"""
        <div style="background-color: #fff8f8; border-radius: 12px; padding: 18px; border: 1px solid #fca5a5; box-shadow: 0 4px 12px rgba(239,68,68,0.06); display: flex; align-items: center; gap: 20px; height: 110px; position: relative; width: 100%;">
            <div style="background-color: #fee2e2; width: 44px; height: 44px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 20px; flex-shrink: 0; border: 1px solid #fca5a5;">🚨</div>
            <div style="flex-grow: 1; display: flex; flex-direction: column; justify-content: space-between; height: 100%;">
                <div style="font-size: 10px; font-weight: 900; color: #b91c1c; text-transform: uppercase; letter-spacing: 0.5px; line-height: 1.2;">🚨 High Severity Observations (Severity 4 & 5)</div>
                <div style="display: flex; justify-content: space-between; align-items: center; width: 100%; margin-top: 6px;">
                    <div style="text-align: center; flex: 1;">
                        <div style="font-size: 8px; font-weight: 800; color: #991b1b; text-transform: uppercase; letter-spacing: 0.5px;">Total Obs</div>
                        <div style="font-size: 22px; font-weight: 950; color: #b91c1c; margin-top: 2px; line-height: 1;">{total_high_sev}</div>
                    </div>
                    <div style="width: 1px; height: 26px; background-color: #fca5a5;"></div>
                    <div style="text-align: center; flex: 1;">
                        <div style="font-size: 8px; font-weight: 800; color: #991b1b; text-transform: uppercase; letter-spacing: 0.5px;">Obs / Day</div>
                        <div style="font-size: 22px; font-weight: 950; color: #d97706; margin-top: 2px; line-height: 1;">{high_sev_per_day:.1f}</div>
                    </div>
                    <div style="width: 1px; height: 26px; background-color: #fca5a5;"></div>
                    <div style="text-align: center; flex: 1;">
                        <div style="font-size: 8px; font-weight: 800; color: #14532d; text-transform: uppercase; letter-spacing: 0.5px;">Closure Rate</div>
                        <div style="font-size: 22px; font-weight: 950; color: #16a34a; margin-top: 2px; line-height: 1;">{high_sev_closure:.0f}%</div>
                    </div>
                </div>
                <div style="width: 30px; height: 3px; background-color: #ef4444; border-radius: 2px; margin-top: 6px;"></div>
            </div>
            <div style="position: absolute; right: 12px; bottom: 8px; font-size: 32px; opacity: 0.04; font-weight: 900;">🚨</div>
        </div>
        """)

    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

    # Charts Grid Row 1
    row1_c1, row1_c2, row1_c3 = st.columns([1.1, 1, 1.2])
    
    with row1_c1:
        with st.container(border=True):
            st.markdown("<h4 style='margin:0; padding-bottom:8px; border-bottom:2px solid #0033a0; color:#002060; font-weight:900; font-size:14px; text-transform:uppercase;'>📊 TOP OBSERVATION CATEGORIES</h4>", unsafe_allow_html=True)
            df_trends = df_filtered[df_filtered['Trend'].notna() & (df_filtered['Trend'] != "") & (df_filtered['Trend'].astype(str).str.lower() != "nan")]
            if not df_trends.empty:
                trend_counts = df_trends['Trend'].value_counts().reset_index()
                trend_counts.columns = ['Category', 'Count']
                trend_counts = trend_counts.sort_values('Count', ascending=True)
                
                # Apply icons to labels
                trend_counts['Category'] = trend_counts['Category'].apply(get_category_label)
                
                fig_trends = px.bar(
                    trend_counts.tail(8),
                    x='Count',
                    y='Category',
                    orientation='h',
                    color_discrete_sequence=['#0b55cc'],
                    text='Count'
                )
                fig_trends.update_layout(
                    margin=dict(l=10, r=25, t=10, b=10),
                    height=240,
                    xaxis_title="",
                    yaxis_title="",
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(family="Inter, sans-serif"),
                    xaxis=dict(showgrid=True, gridcolor="#e2e8f0"),
                    yaxis=dict(showgrid=False, tickfont=dict(size=11, color="#0f172a", weight="bold"))
                )
                fig_trends.update_traces(textposition='outside', textfont=dict(size=11, color="#000000", weight="bold"))
                st.plotly_chart(fig_trends, use_container_width=True, config={'displayModeBar': False})
            else:
                st.markdown("<div style='height:240px; display:flex; align-items:center; justify-content:center; color:#0f172a; font-size:14px; font-weight:bold;'>No classified Trend data in this date range.</div>", unsafe_allow_html=True)
            
    with row1_c2:
        with st.container(border=True):
            st.markdown("<h4 style='margin:0; padding-bottom:8px; border-bottom:2px solid #0033a0; color:#002060; font-weight:900; font-size:14px; text-transform:uppercase;'>🧭 ACTION / CONDITION RATIO</h4>", unsafe_allow_html=True)
            
            # Gauge colors visible - transparent indicator bar + bright gauge steps + analog needle pointer arrow
            fig_gauge = go.Figure(go.Indicator(
                mode = "gauge",
                value = unsafe_ratio,
                domain = {'x': [0, 1], 'y': [0, 1]},
                gauge = {
                    'axis': {'range': [0, 1.5], 'tickwidth': 1.5, 'tickcolor': "#000000", 'tickfont': {'weight': 'bold', 'color': '#000000'}},
                    'bar': {'color': "rgba(0,0,0,0)"}, # Completely transparent bar to keep background color steps visible
                    'steps': [
                        {'range': [0, 0.5], 'color': "#22c55e"},   # Green (0 to 0.5)
                        {'range': [0.5, 1.0], 'color': "#eab308"},   # Yellow/Gold (0.5 to 1.0)
                        {'range': [1.0, 1.5], 'color': "#ef4444"}    # Red (1.0 to 1.5)
                    ]
                }
            ))
            
            # Calculate angle and coordinates for custom analog arrow needle
            import math
            # Semicircle goes from pi to 0 (180 to 0 degrees)
            theta = math.pi - (min(unsafe_ratio, 1.5) / 1.5) * math.pi
            
            # Tip of needle pointing to arc
            x_end = 0.5 + 0.28 * math.cos(theta)
            y_end = 0.15 + 0.28 * math.sin(theta)
            
            # Base of needle perpendicular to angle (with a nice width for arrow look)
            dx = 0.01 * math.cos(theta - math.pi/2)
            dy = 0.01 * math.sin(theta - math.pi/2)
            
            x_base_left = 0.5 - dx
            y_base_left = 0.15 - dy
            x_base_right = 0.5 + dx
            y_base_right = 0.15 + dy
            
            path_str = f"M {x_base_left} {y_base_left} L {x_base_right} {y_base_right} L {x_end} {y_end} Z"
            
            fig_gauge.update_layout(
                margin=dict(l=20, r=20, t=10, b=0),
                height=180,
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(family="Inter, sans-serif"),
                shapes=[
                    # Pointer needle shape (arrow/wedge)
                    dict(
                        type="path",
                        path=path_str,
                        fillcolor="#002256",
                        line=dict(color="#002256", width=1)
                    ),
                    # Center circle hub
                    dict(
                        type="circle",
                        xref="paper", yref="paper",
                        x0=0.485, y0=0.135, x1=0.515, y1=0.165,
                        fillcolor="#002256",
                        line=dict(color="#002256")
                    )
                ]
            )
            st.plotly_chart(fig_gauge, use_container_width=True, config={'displayModeBar': False})
            
            # Keep all text labels below the gauge (arrow) to avoid any overlapping
            status_text = "Low Action vs Conditions" if unsafe_ratio < 0.6 else ("Moderate Action vs Conditions" if unsafe_ratio < 1.0 else "High Action vs Conditions")
            st.markdown(f"""
            <div style='text-align:center; font-family:Inter, sans-serif; margin-top:-35px; margin-bottom:5px; padding-bottom:5px;'>
                <div style='font-size:32px; font-weight:900; color:#000000; line-height:1;'>{unsafe_ratio:.3f}</div>
                <div style='font-size:11.5px; font-weight:800; color:#1e293b; margin-top:2px; text-transform:uppercase;'>{status_text}</div>
                <div style='font-size:12px; color:#0f172a; font-weight:700; margin-top:6px;'>Acts: <b>{unsafe_acts}</b> &nbsp;|&nbsp; Conditions: <b>{unsafe_cond}</b></div>
            </div>
            """, unsafe_allow_html=True)
        
    with row1_c3:
        with st.container(border=True):
            st.markdown("<h4 style='margin:0; padding-bottom:8px; border-bottom:2px solid #0033a0; color:#002060; font-weight:900; font-size:14px; text-transform:uppercase;'>📍 ZONE WISE AVERAGE SEVERITY</h4>", unsafe_allow_html=True)
            df_zones = df_filtered[df_filtered['Zone'].notna() & (df_filtered['Zone'] != "") & (df_filtered['Zone'].astype(str).str.lower() != "nan")]
            if not df_zones.empty:
                zone_severity = df_zones.groupby('Zone')['Severity'].mean().reset_index()
                zone_severity.columns = ['Zone', 'Avg Severity']
                zone_severity = zone_severity.sort_values('Avg Severity', ascending=True)
                
                # Colour code zone wise avg severity bars as: 0-2 green, 2-3 is orange, 3-5 is red
                colors_zones = []
                for val in zone_severity['Avg Severity']:
                    if val >= 3.0:
                        colors_zones.append('#d93838')  # Red
                    elif val >= 2.0:
                        colors_zones.append('#f5a623')  # Orange
                    else:
                        colors_zones.append('#27ae60')  # Green
                
                fig_zones = px.bar(
                    zone_severity,
                    x='Avg Severity',
                    y='Zone',
                    orientation='h',
                    text=zone_severity['Avg Severity'].apply(lambda x: f"{x:.1f}")
                )
                fig_zones.update_traces(marker_color=colors_zones, textposition='outside', textfont=dict(size=11, color="#000000", weight="bold"))
                fig_zones.update_layout(
                    margin=dict(l=10, r=25, t=10, b=10),
                    height=240,
                    xaxis_title="",
                    yaxis_title="",
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(family="Inter, sans-serif"),
                    xaxis=dict(range=[0, 5], dtick=1, showgrid=True, gridcolor="#e2e8f0"),
                    yaxis=dict(showgrid=False, tickfont=dict(size=11, color="#0f172a", weight="bold"))
                )
                st.plotly_chart(fig_zones, use_container_width=True, config={'displayModeBar': False})
            else:
                st.markdown("<div style='height:240px; display:flex; align-items:center; justify-content:center; color:#0f172a; font-size:14px; font-weight:bold;'>No Zone data in this date range.</div>", unsafe_allow_html=True)

    # Row 2 Analysis Grid
    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
    row2_c1, row2_c2 = st.columns([1.3, 1])
    
    with row2_c1:
        with st.container(border=True):
            st.markdown("<h4 style='margin:0; padding-bottom:8px; border-bottom:2px solid #0033a0; color:#002060; font-weight:900; font-size:14px; text-transform:uppercase;'>👥 CONTRACTOR WISE AVERAGE SEVERITY SCORE</h4>", unsafe_allow_html=True)
            if not df_valid_contractors.empty:
                contractor_severity = df_valid_contractors.groupby('Contractor name')['Severity'].mean().reset_index()
                contractor_severity.columns = ['Contractor', 'Avg Severity']
                # Sort by Average Severity
                contractor_severity = contractor_severity.sort_values('Avg Severity', ascending=True)
                
                # Dynamic severity coloring based on reference mockup
                colors_contractors = [get_severity_color(val) for val in contractor_severity['Avg Severity']]
                
                fig_contractors = px.bar(
                    contractor_severity,
                    x='Avg Severity',
                    y='Contractor',
                    orientation='h',
                    text=contractor_severity['Avg Severity'].apply(lambda x: f"{x:.1f}")
                )
                fig_contractors.update_traces(marker_color=colors_contractors, textposition='outside', textfont=dict(size=11, color="#000000", weight="bold"))
                fig_contractors.update_layout(
                    margin=dict(l=10, r=25, t=10, b=10),
                    height=300,
                    xaxis_title="Average Severity Score",
                    yaxis_title="",
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(family="Inter, sans-serif"),
                    xaxis=dict(range=[0, 5], dtick=1, showgrid=True, gridcolor="#e2e8f0"),
                    yaxis=dict(showgrid=False, tickfont=dict(size=11, color="#0f172a", weight="bold"))
                )
                st.plotly_chart(fig_contractors, use_container_width=True, config={'displayModeBar': False})
            else:
                st.markdown("<div style='height:300px; display:flex; align-items:center; justify-content:center; color:#0f172a; font-size:14px; font-weight:bold;'>No contractor observations in this date range.</div>", unsafe_allow_html=True)
            
    with row2_c2:
        # Build High Severity Trend dynamically with pure HTML layout matching reference mockup
        period_days = (end_date - start_date).days
        prior_end = start_date - timedelta(days=1)
        prior_start = prior_end - timedelta(days=period_days)
        
        curr_high = df_valid_contractors[df_valid_contractors['Severity'].isin([4, 5])]
        curr_counts = curr_high['Contractor name'].value_counts().reset_index()
        curr_counts.columns = ['Contractor', 'Current Period']
        
        # Prior period data
        df_prior = df_raw[(df_raw['Date'].dt.date >= prior_start) & (df_raw['Date'].dt.date <= prior_end)] if 'Date' in df_raw.columns else pd.DataFrame()
        if not df_prior.empty:
            prior_valid_contractors = df_prior[df_prior['Contractor name'].notna() & ~df_prior['Contractor name'].astype(str).str.lower().str.strip().isin(ignore_contractors)]
            prior_high = prior_valid_contractors[prior_valid_contractors['Severity'].isin([4, 5])]
            prior_counts = prior_high['Contractor name'].value_counts().reset_index()
            prior_counts.columns = ['Contractor', 'Prior Period']
        else:
            prior_counts = pd.DataFrame(columns=['Contractor', 'Prior Period'])
        
        merged_trend = pd.merge(curr_counts, prior_counts, on='Contractor', how='outer').fillna(0)
        merged_trend['Current Period'] = merged_trend['Current Period'].astype(int)
        merged_trend['Prior Period'] = merged_trend['Prior Period'].astype(int)
        merged_trend['Diff'] = merged_trend['Current Period'] - merged_trend['Prior Period']
        
        merged_trend = merged_trend.sort_values('Current Period', ascending=False)
        
        trend_rows = []
        for idx, r in merged_trend.iterrows():
            trend_rows.append({
                "Contractor": r['Contractor'].title(),
                "Current Period": r['Current Period'],
                "Diff": r['Diff']
            })
            
        rows_html = ""
        if trend_rows:
            for idx, r in enumerate(trend_rows[:5]):
                bg_color = "#ffffff" if idx % 2 == 0 else "#f8fafc"
                diff_val = r["Diff"]
                if diff_val > 0:
                    change_html = f"<span style='color: #dc2626; font-weight: 800;'>▲ +{diff_val}</span>"
                elif diff_val < 0:
                    change_html = f"<span style='color: #16a34a; font-weight: 800;'>▼ {diff_val}</span>"
                else:
                    change_html = f"<span style='color: #0f172a; font-weight: 800;'>➖ 0</span>"
                    
                rows_html += f"""
                <tr style="background-color: {bg_color}; border-bottom: 1px solid #cbd5e1; font-size: 12.5px; color: #0f172a;">
                    <td style="padding: 10px; font-weight: 700;">{r['Contractor']}</td>
                    <td style="padding: 10px; text-align: center; font-weight: 800;">{r['Current Period']}</td>
                    <td style="padding: 10px; text-align: center;">{change_html}</td>
                </tr>
                """
        else:
            rows_html = """
            <tr style="background-color: #ffffff;">
                <td colspan="3" style="padding: 20px; text-align: center; color: #0f172a; font-weight: bold; font-style: italic;">No high severity observations found in either period.</td>
            </tr>
            """
            
        trend_card_html = f"""
        <div style="background-color: #ffffff; border-radius: 12px; border: 1px solid #cbd5e1; box-shadow: 0 4px 12px rgba(0,34,86,0.06); padding: 18px; height: 100%;">
            <h4 style="margin:0; padding-bottom:8px; border-bottom:2px solid #0033a0; color:#002060; font-weight:900; font-size:14px; text-transform:uppercase; display:flex; align-items:center; gap:8px;">
                📈 HIGH SEVERITY TREND (SELECTED VS PRIOR PERIOD)
            </h4>
            <div style="margin-top: 15px; overflow-x: auto;">
                <table style="width: 100%; border-collapse: collapse; text-align: left; font-family: 'Inter', sans-serif;">
                    <thead>
                        <tr style="background-color: #0b3c95; color: #ffffff; font-size: 11.5px;">
                            <th style="padding: 10px; font-weight: 800; border-top-left-radius: 6px; border-bottom-left-radius: 6px;">Contractor</th>
                            <th style="padding: 10px; font-weight: 800; text-align: center;">High Severity Obs (Current)</th>
                            <th style="padding: 10px; font-weight: 800; text-align: center; border-top-right-radius: 6px; border-bottom-right-radius: 6px;">Change from Prior</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>
            </div>
            <div style="background-color: #f0f5ff; border-radius: 8px; padding: 12px; margin-top: 15px; border: 1px solid #cbd5e1;">
                <div style="font-size: 11.5px; font-weight: 900; color: #0b3c95; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.5px;">Action Items:</div>
                <div style="font-size: 11.5px; color: #0f172a; font-weight: 700; line-height: 1.5; display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
                    <span style="font-size: 13px;">🔍</span>
                    <span>Conduct immediate reviews and discussions with high-risk contractor owners.</span>
                </div>
                <div style="font-size: 11.5px; color: #0f172a; font-weight: 700; line-height: 1.5; display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 13px;">📅</span>
                    <span>Hold daily/weekly on-ground review meetings to check and correct conditions.</span>
                </div>
            </div>
        </div>
        """
        render_html(trend_card_html)

    # Sync Observation categories warning helper
    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("<h4 style='margin:0; padding-bottom:8px; border-bottom:2px solid #0033a0; color:#002060; font-weight:900; font-size:14px; text-transform:uppercase;'>📋 Pending Tasks & Data Quality Sync Helper</h4>", unsafe_allow_html=True)
        
        df_missing_trend = df_raw[df_raw['Trend'].isna() | (df_raw['Trend'] == "") | (df_raw['Trend'].astype(str).str.lower() == "nan")].copy() if not df_raw.empty else pd.DataFrame()
        
        if not df_missing_trend.empty:
            st.warning(f"⚠️ There are {len(df_missing_trend)} observations in the Excel sheet that are missing a Trend classification. Please classify them in the Excel sheet.")
            
            # Select columns to display
            cols_to_disp = ['ln', 'Date', 'Contractor name', 'Observation Discription ', 'Severity ']
            disp_cols = [c for c in cols_to_disp if c in df_missing_trend.columns]
            
            df_missing_display = df_missing_trend[disp_cols].copy()
            if 'Date' in df_missing_display.columns:
                df_missing_display['Date'] = df_missing_display['Date'].dt.strftime('%d-%b-%Y')
            
            # Rename for display
            df_missing_display.columns = [c.strip().replace('ln', 'Row # (ln)').replace('Observation Discription ', 'Observation Description').replace('Contractor name', 'Contractor') for c in disp_cols]
            
            st.dataframe(df_missing_display.head(15), hide_index=True, use_container_width=True)
            st.caption("ℹ️ Only showing the first 15 records. Please assign a category (e.g. PPE, Work at Height, Housekeeping, Electrical, etc.) in the Excel sheet.")
        else:
            st.success("✅ All sync observations have been classified! Excellent data quality.")
