import os
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

from config.dashboard_config import DEFAULT_TOOLS_PATH, S3_CACHE_DIR, load_config, save_config
from utils.data_loaders import load_tools_data
from dashboards import render_source_selector

def render_kpi_metric(title, emoji, value, color, subtitle=None):
    sub_html = ""
    if subtitle:
        badge_bg = "#fee2e2" if "overdue" in subtitle.lower() or "rejected" in subtitle.lower() else "#e8f5e9"
        badge_text = "#991b1b" if "overdue" in subtitle.lower() or "rejected" in subtitle.lower() else "#2e7d32"
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

def render_tools_tackles_dashboard():
    # 1. Render data source selector
    source_type = render_source_selector("tools")
    
    config = load_config()
    current_tools_path = config.get("tools_path", DEFAULT_TOOLS_PATH)
    path_exists = True
    
    if source_type == "aws":
        aws_path = os.path.join(S3_CACHE_DIR, os.path.basename(DEFAULT_TOOLS_PATH))
        df_raw = load_tools_data(aws_path)
        path_exists = os.path.exists(aws_path)
        
    else:  # upload mode
        uploaded_file = st.session_state.get("tools_file")
        if uploaded_file is not None:
            df_raw = load_tools_data(uploaded_file)
            path_exists = True
        else:
            df_raw = pd.DataFrame()
            path_exists = False

    st.sidebar.markdown("<hr style='border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
    st.sidebar.markdown("<h2 style='text-align: center; color: white;'>⚙️ CONTROLS</h2>", unsafe_allow_html=True)

    if st.sidebar.button("🔄 Refresh Tools Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    # Connection Status indicator in sidebar
    if path_exists and not df_raw.empty:
        st.sidebar.success(f"✅ Excel Connected!\nParsed {len(df_raw)} total equipment records.")
    else:
        st.sidebar.warning("⚠️ Excel File Not Connected!")

    date_display_str = "Q2 FY26"
    
    st.markdown(f"""
    <div class="dashboard-header">
        <div class="header-title-box">
            <div class="header-main-title">CONTRACTOR EQUIPMENT & TOOLS COMPLIANCE TRACKER</div>
            <div class="header-sub-title"></div>
        </div>
        <div class="header-info-box">
            <div class="header-info-lbl">Reporting Window</div>
            <div class="header-info-date">📅 {date_display_str}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if source_type == "aws" and not path_exists:
        st.warning("⚠️ AWS S3 local cache not found. Please click '☁️ Sync AWS' first in the sidebar to sync your files.")
        return
    elif source_type == "upload" and not path_exists:
        st.warning("⚠️ Please upload the Tools & Tackles Excel tracker in the sidebar to render the dashboard.")
        return
    elif df_raw.empty:
        st.warning("⚠️ The loaded dataset is empty or could not be parsed.")
        return

    # --- Calculations ---
    total_tools = len(df_raw)
    good_tools = df_raw[df_raw['Condition'] == 'Good'].shape[0]
    rejected_tools = df_raw[df_raw['Condition'] == 'Rejected'].shape[0]
    
    # Check overdue inspections (Due Date < Today)
    today = datetime.now()
    overdue_df = df_raw[(df_raw['Inspection Due Date'].notna()) & (df_raw['Inspection Due Date'] < today)]
    total_overdue = len(overdue_df)
    
    pct_fit = (good_tools / total_tools * 100) if total_tools > 0 else 0
    pct_rejected = (rejected_tools / total_tools * 100) if total_tools > 0 else 0
    pct_overdue = (total_overdue / total_tools * 100) if total_tools > 0 else 0

    # KPI Layout
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        with st.container(border=True):
            render_kpi_metric("Total Registered Tools", "🛠️", f"{total_tools:,}", "#0033a0", "All contractor equipment")
    with col2:
        with st.container(border=True):
            render_kpi_metric("Fit For Use (Good)", "✅", f"{good_tools:,}", "#10b981", f"{pct_fit:.0f}% of total inventory")
    with col3:
        with st.container(border=True):
            render_kpi_metric("Defective / Rejected", "❌", f"{rejected_tools:,}", "#fa5252", f"{pct_rejected:.0f}% rejected - replace/repair")
    with col4:
        with st.container(border=True):
            render_kpi_metric("Overdue Inspections", "⏰", f"{total_overdue:,}", "#e67e22", f"{pct_overdue:.0f}% expired certs")

    # Interactive Filters in Sidebar
    st.sidebar.markdown("<hr style='border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
    st.sidebar.markdown("<h4 style='color: white;'>🔍 FILTERS</h4>", unsafe_allow_html=True)
    
    # 1. Search Box
    search_query = st.sidebar.text_input("Search Tool Name / ID", "")
    
    # 2. Contractor Select
    all_contractors = sorted(df_raw['Contractor Name'].dropna().unique())
    selected_contractors = st.sidebar.multiselect("Contractors", all_contractors, default=[])
    
    # 3. Category Select
    all_categories = sorted(df_raw['Category'].dropna().unique())
    selected_categories = st.sidebar.multiselect("Tool Categories", all_categories, default=[])
    
    # 4. Status select
    selected_status = st.sidebar.multiselect("Condition Status", ["Good", "Rejected"], default=[])

    # Apply Filters
    df_filtered = df_raw.copy()
    if search_query:
        df_filtered = df_filtered[
            df_filtered['Tool Name'].astype(str).str.lower().str.contains(search_query.lower()) |
            df_filtered['Tool ID'].astype(str).str.lower().str.contains(search_query.lower())
        ]
    if selected_contractors:
        df_filtered = df_filtered[df_filtered['Contractor Name'].isin(selected_contractors)]
    if selected_categories:
        df_filtered = df_filtered[df_filtered['Category'].isin(selected_categories)]
    if selected_status:
        df_filtered = df_filtered[df_filtered['Condition'].isin(selected_status)]

    # Layout Row 1: Charts
    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
    c1, c2 = st.columns([1.2, 1])
    
    with c1:
        with st.container(border=True):
            st.markdown("<h4 style='margin:0; padding-bottom:8px; border-bottom:2px solid #0033a0; color:#002060; font-weight:800; font-size:14px; text-transform:uppercase;'>📊 EQUIPMENT DISTRIBUTION BY CATEGORY</h4>", unsafe_allow_html=True)
            cat_counts = df_filtered['Category'].value_counts().reset_index()
            cat_counts.columns = ['Category', 'Count']
            cat_counts = cat_counts.sort_values('Count', ascending=True)
            
            if not cat_counts.empty:
                fig_cat = px.bar(
                    cat_counts,
                    x='Count',
                    y='Category',
                    orientation='h',
                    color_discrete_sequence=['#0055b8'],
                    text='Count'
                )
                fig_cat.update_layout(
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
                st.plotly_chart(fig_cat, use_container_width=True, config={'displayModeBar': False})
            else:
                st.markdown("<div style='height:240px; display:flex; align-items:center; justify-content:center; color:#64748b;'>No matching data.</div>", unsafe_allow_html=True)

    with c2:
        with st.container(border=True):
            st.markdown("<h4 style='margin:0; padding-bottom:8px; border-bottom:2px solid #0033a0; color:#002060; font-weight:800; font-size:14px; text-transform:uppercase;'>🏗️ CONDITION COMPLIANCE BY CONTRACTOR</h4>", unsafe_allow_html=True)
            
            if not df_filtered.empty:
                # Group by Contractor & Condition
                grouped = df_filtered.groupby(['Contractor Name', 'Condition']).size().unstack(fill_value=0).reset_index()
                # Ensure both columns exist
                for col in ['Good', 'Rejected']:
                    if col not in grouped.columns:
                        grouped[col] = 0
                grouped['Total'] = grouped['Good'] + grouped['Rejected']
                grouped = grouped.sort_values('Total', ascending=False).head(8) # Top 8
                
                fig_cond = go.Figure()
                fig_cond.add_trace(go.Bar(
                    y=grouped['Contractor Name'],
                    x=grouped['Good'],
                    name='Good',
                    orientation='h',
                    marker_color='#10b981'
                ))
                fig_cond.add_trace(go.Bar(
                    y=grouped['Contractor Name'],
                    x=grouped['Rejected'],
                    name='Rejected',
                    orientation='h',
                    marker_color='#ef4444'
                ))
                fig_cond.update_layout(
                    barmode='stack',
                    margin=dict(l=10, r=10, t=10, b=10),
                    height=240,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(family="Inter, sans-serif"),
                    xaxis=dict(showgrid=True, gridcolor="#f1f5f9"),
                    yaxis=dict(showgrid=False)
                )
                st.plotly_chart(fig_cond, use_container_width=True, config={'displayModeBar': False})
            else:
                st.markdown("<div style='height:240px; display:flex; align-items:center; justify-content:center; color:#64748b;'>No matching data.</div>", unsafe_allow_html=True)

    # Layout Row 2: Drill-down & Data Explorer
    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("<h4 style='margin:0; padding-bottom:8px; border-bottom:2px solid #0033a0; color:#002060; font-weight:800; font-size:14px; text-transform:uppercase;'>🔍 DETAILED EQUIPMENT EXPLORER & DRILL-DOWN</h4>", unsafe_allow_html=True)
        
        # Show count of filtered items
        st.markdown(f"Showing **{len(df_filtered)}** of **{total_tools}** total items.")
        
        # Format dates for table display
        df_display = df_filtered.copy()
        if not df_display.empty:
            df_display['Inspection Date'] = df_display['Inspection Date'].apply(lambda x: x.strftime('%d-%b-%Y') if pd.notna(x) else "")
            df_display['Inspection Due Date'] = df_display['Inspection Due Date'].apply(lambda x: x.strftime('%d-%b-%Y') if pd.notna(x) else "")
            
            st.dataframe(df_display, hide_index=True, use_container_width=True, height=280)
            
            # Export Options
            csv = df_filtered.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Export Filtered Equipment to CSV",
                data=csv,
                file_name="Contractor_Equipment_Report.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.info("No matching records found. Modify your filters in the sidebar.")
