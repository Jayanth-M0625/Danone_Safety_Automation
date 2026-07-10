import os
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go

from config.dashboard_config import DEFAULT_CSFA_PATH, S3_CACHE_DIR, load_config, save_config
from utils.data_loaders import load_csfa_data
from dashboards import render_source_selector

def render_csfa_dashboard():
    # Render Data Source Selector in Sidebar
    source_type = render_source_selector("csfa")
    
    # Sidebar File Path Settings (Only show when in Local Mode)
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

    # KPI Layout
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

    # Charts Grid Row 1
    row1_c1, row1_c2, row1_c3 = st.columns([1, 1, 1.2])
    
    with row1_c1:
        with st.container(border=True):
            st.markdown("<h4 style='margin:0; padding-bottom:8px; border-bottom:2px solid #0033a0; color:#002060; font-weight:800; font-size:14px; text-transform:uppercase;'>📊 TOP OBSERVATION CATEGORIES</h4>", unsafe_allow_html=True)
            df_trends = df_filtered[df_filtered['Trend'].notna() & (df_filtered['Trend'] != "") & (df_filtered['Trend'].astype(str).str.lower() != "nan")]
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
            st.markdown("<h4 style='margin:0; padding-bottom:8px; border-bottom:2px solid #0033a0; color:#002060; font-weight:800; font-size:14px; text-transform:uppercase;'>🛡️ ZONE WISE AVERAGE SEVERITY</h4>", unsafe_allow_html=True)
            df_zones = df_filtered[df_filtered['Zone'].notna() & (df_filtered['Zone'] != "") & (df_filtered['Zone'].astype(str).str.lower() != "nan")]
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

    # Row 2 Analysis Grid
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

    # Sync Observation categories warning helper
    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("<h4 style='margin:0; padding-bottom:8px; border-bottom:2px solid #0033a0; color:#002060; font-weight:800; font-size:14px; text-transform:uppercase;'>📋 Pending Tasks & Data Quality Sync Helper</h4>", unsafe_allow_html=True)
        
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
