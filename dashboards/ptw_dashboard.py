import os
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from typing import Dict, Any

from config.dashboard_config import DEFAULT_PTW_PATH, DEFAULT_PTW_AUDIT_PATH, S3_CACHE_DIR, load_config, save_config
from utils.data_loaders import load_ptw_data
from dashboards import render_source_selector

# --- Static Fallback Data ---
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

# --- HTML Rendering Helpers ---
def render_html(html_str):
    """Renders HTML directly to Streamlit, bypassing markdown parsing completely to avoid code block issues."""
    st.html(html_str)

def pad_rows_to_three(rows):
    """Pads list of rows to exactly 3 elements for layout symmetry and vertical alignment."""
    padded = [list(r) for r in rows]
    while len(padded) < 3:
        next_idx = len(padded) + 1
        padded.append([next_idx, "", ""])
    return padded

def render_kpi_metric(title, emoji, value, accent_color, badge_bg, badge_border):
    """Renders a beautifully styled KPI card matching the CSFA dashboard styling with high contrast text."""
    html = f"""
    <div style="background-color: #ffffff; border-radius: 12px; padding: 15px; border: 1px solid #cbd5e1; box-shadow: 0 4px 12px rgba(0,34,86,0.06); display: flex; align-items: center; gap: 12px; height: 105px; position: relative;">
        <div style="background-color: {badge_bg}; width: 38px; height: 38px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 16px; flex-shrink: 0; border: 1px solid {badge_border};">{emoji}</div>
        <div style="flex-grow: 1; display: flex; flex-direction: column; justify-content: center;">
            <div style="font-size: 11px; font-weight: 900; color: #1e293b; text-transform: uppercase; letter-spacing: 0.5px; line-height: 1.2;">{title}</div>
            <div style="font-size: 22px; font-weight: 950; color: {accent_color}; line-height: 1; margin-top: 4px;">{value}</div>
            <div style="width: 25px; height: 3px; background-color: {accent_color}; border-radius: 2px; margin-top: 5px;"></div>
        </div>
    </div>
    """
    render_html(html)

def generate_html_table(title, headers, rows):
    """Generates an HTML table styled identically to the CSFA dashboard tables (dark-blue headers, bold text)."""
    header_cols_html = ""
    for idx, h in enumerate(headers):
        border_radius = ""
        if idx == 0:
            border_radius = "border-top-left-radius: 6px; border-bottom-left-radius: 6px;"
        elif idx == len(headers) - 1:
            border_radius = "border-top-right-radius: 6px; border-bottom-right-radius: 6px;"
        header_cols_html += f"<th style='padding: 10px; font-weight: 800; border: none; text-align: center; {border_radius}'>{h}</th>"
        
    rows_html = ""
    for r_idx, r in enumerate(rows):
        bg_color = "#ffffff" if r_idx % 2 == 0 else "#f8fafc"
        row_cols_html = ""
        for c_idx, val in enumerate(r):
            align = "center" if c_idx == 0 or isinstance(val, (int, float)) or (isinstance(val, str) and val.isdigit()) else "left"
            weight = "800" if c_idx == 0 or (c_idx == len(r) - 1) else "700"
            row_cols_html += f"<td style='padding: 10px; text-align: {align}; font-weight: {weight}; border: none;'>{val}</td>"
        rows_html += f"<tr style='background-color: {bg_color}; border-bottom: 1px solid #cbd5e1; font-size: 12px; color: #0f172a;'>{row_cols_html}</tr>"
        
    html = f"""
    <div style="background-color: #ffffff; border-radius: 12px; border: 1px solid #cbd5e1; box-shadow: 0 4px 12px rgba(0,34,86,0.06); padding: 18px; margin-bottom: 20px; font-family: 'Inter', sans-serif;">
        <h4 style="margin: 0; padding-bottom: 10px; border-bottom: 2px solid #0033a0; color: #002060; font-weight: 900; font-size: 14px; text-transform: uppercase; display: flex; align-items: center; gap: 8px;">
            {title}
        </h4>
        <div style="margin-top: 15px; overflow-x: auto;">
            <table style="width: 100%; border-collapse: collapse; text-align: left;">
                <thead>
                    <tr style="background-color: #0b3c95; color: #ffffff; font-size: 11px;">
                        {header_cols_html}
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
        </div>
    </div>
    """
    return html

def render_donut_chart(compliance_val):
    """Renders a high contrast compliance donut chart with bold/dark center labels."""
    fig = go.Figure(data=[go.Pie(
        labels=['Compliance', 'Gap'],
        values=[compliance_val, max(0, 100 - compliance_val)],
        hole=.7,
        marker=dict(colors=['#22c55e', '#e2e8f0']),
        textinfo='none',
        hoverinfo='label+percent'
    )])
    
    fig.update_layout(
        showlegend=False,
        annotations=[dict(
            text=f"<span style='font-size:32px; font-weight:950; color:#16a34a; font-family:\"Inter\", sans-serif;'>{compliance_val}%</span>",
            x=0.5, y=0.5,
            showarrow=False
        )],
        margin=dict(l=10, r=10, t=10, b=10),
        height=180,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    return fig

def load_precalculated_ptw_metrics(ptw_source) -> Any:
    """Loads pre-calculated metrics from the 'PTW Dashboard Data' sheet if it exists."""
    if ptw_source is None:
        return None
    try:
        xl = pd.ExcelFile(ptw_source)
        if "PTW Dashboard Data" in xl.sheet_names:
            df = xl.parse("PTW Dashboard Data")
            
            # Row 0 contains overall metrics
            total_issued = int(df.iloc[0, 0]) if pd.notna(df.iloc[0, 0]) else 0
            total_closed = int(df.iloc[0, 1]) if pd.notna(df.iloc[0, 1]) else 0
            total_audited = int(df.iloc[0, 2]) if pd.notna(df.iloc[0, 2]) else 0
            total_observations = int(df.iloc[0, 3]) if pd.notna(df.iloc[0, 3]) else 0
            critical_observations = int(df.iloc[0, 4]) if pd.notna(df.iloc[0, 4]) else 0
            
            compliance_val = df.iloc[0, 5]
            if pd.notna(compliance_val):
                try:
                    compliance = int(float(compliance_val))
                except ValueError:
                    compliance = int(float(str(compliance_val).replace('%', '').strip()))
            else:
                compliance = 100
                
            high_risk_issued = int(df.iloc[0, 6]) if pd.notna(df.iloc[0, 6]) else 0
            high_risk_safely_executed = int(df.iloc[0, 7]) if pd.notna(df.iloc[0, 7]) else 0
            high_risk_observations = int(df.iloc[0, 8]) if pd.notna(df.iloc[0, 8]) else 0
            
            # Top 3 violators
            violators = []
            for idx, r in enumerate([3, 4, 5]):
                if r < len(df):
                    val = df.iloc[r, 0]
                    count = df.iloc[r, 1]
                    if pd.notna(val) and str(val).strip() != "" and str(val).strip() != "0" and str(val).strip() != "nan":
                        violators.append([idx + 1, str(val).strip(), int(count) if pd.notna(count) else 0])
            
            top3_obs_sum = sum(count for _, _, count in violators)
            violators_contrib = int(top3_obs_sum / total_observations * 100) if total_observations > 0 else 0
            
            # Top 3 high risk observations
            obs_counts = {}
            if "HighRiskObs" in xl.sheet_names:
                try:
                    df_hr_obs = xl.parse("HighRiskObs")
                    obs_col = [c for c in df_hr_obs.columns if "observation" in c.lower() and "categor" not in c.lower()]
                    count_col = 'Unnamed: 3' if 'Unnamed: 3' in df_hr_obs.columns else 'Count'
                    if obs_col and count_col in df_hr_obs.columns:
                        for _, r in df_hr_obs.iterrows():
                            o_val = r[obs_col[0]]
                            c_val = r[count_col]
                            if pd.notna(o_val) and pd.notna(c_val):
                                try:
                                    obs_counts[str(o_val).strip().lower()] = int(float(c_val))
                                except ValueError:
                                    pass
                except Exception:
                    pass
                    
            high_risk_obs = []
            for idx, r in enumerate([3, 4, 5]):
                if r < len(df):
                    val = df.iloc[r, 2]
                    if pd.notna(val) and str(val).strip() != "" and str(val).strip() != "nan":
                        val_str = str(val).strip()
                        count = obs_counts.get(val_str.lower(), 1)
                        high_risk_obs.append([idx + 1, val_str, count])
                        
            # Top categories
            category_counts = {}
            if "PTW Audit" in xl.sheet_names:
                try:
                    df_audit_raw = xl.parse("PTW Audit")
                    cat_cols = [c for c in df_audit_raw.columns if "Category" in c]
                    for col in cat_cols:
                        for val in df_audit_raw[col].dropna():
                            val = str(val).strip()
                            category_counts[val] = category_counts.get(val, 0) + 1
                except Exception:
                    pass
                    
            categories = []
            for idx, r in enumerate([3, 4, 5]):
                if r < len(df):
                    val = df.iloc[r, 3]
                    if pd.notna(val) and str(val).strip() != "" and str(val).strip() != "0" and str(val).strip() != "nan":
                        val_str = str(val).strip()
                        count = category_counts.get(val_str, 1)
                        categories.append([idx + 1, val_str, count])
                        
            return {
                'total_issued': total_issued,
                'total_closed': total_closed,
                'total_audited': total_audited,
                'total_observations': total_observations,
                'critical_observations': critical_observations,
                'compliance': compliance,
                'compliance_donut': compliance,
                'high_risk_issued': high_risk_issued,
                'high_risk_safely_executed': high_risk_safely_executed,
                'high_risk_observations': high_risk_observations,
                'violators': violators if violators else [[1, 'None', 0]],
                'violators_contrib': violators_contrib,
                'high_risk_obs': high_risk_obs if high_risk_obs else [[1, 'None', 0]],
                'categories': categories if categories else [[1, 'None', 0]]
            }
    except Exception:
        pass
    return None

# --- Core Dynamic Calculations ---
def compute_ptw_metrics(df_ptw: pd.DataFrame, df_audit: pd.DataFrame) -> Dict[str, Any]:
    """Dynamically calculates PTW KPI metrics and tables from dataframes."""
    if df_ptw.empty or df_audit.empty:
        return STATIC_PTW
        
    try:
        # 1. Row counts
        total_issued = len(df_ptw)
        total_audited = len(df_audit)
        
        # 2. Closed status: check non-null Completion time
        total_closed = df_ptw['Completion time'].notna().sum() if 'Completion time' in df_ptw.columns else total_issued
        
        # 3. Observations columns in audit
        obs_cols = [c for c in df_audit.columns if "Observation" in c and any(x in c for x in ["1st", "2nd", "3rd", "4th", "5th"])]
        sev_cols = [c for c in df_audit.columns if "Severity" in c and any(x in c for x in ["1st", "2nd", "3rd", "4th", "5th"])]
        cat_cols = [c for c in df_audit.columns if "Category" in c and any(x in c for x in ["1st", "2nd", "3rd", "4th", "5th"])]
        
        total_observations = 0
        critical_observations = 0
        
        # Flatten observations list to count and sort
        all_obs_list = []
        all_crit_obs_list = []
        contractor_obs = {}
        category_counts = {}
        
        for _, row in df_audit.iterrows():
            contractor = str(row.get('Contractor', 'Unknown')).strip()
            if contractor.lower() == 'nan' or not contractor:
                contractor = "Unknown"
                
            row_obs_count = 0
            for i, obs_col in enumerate(obs_cols):
                obs_val = str(row[obs_col]).strip() if obs_col in row and pd.notna(row[obs_col]) else ""
                if obs_val and obs_val.lower() not in ["nan", "none", "no observation", "nil"]:
                    row_obs_count += 1
                    total_observations += 1
                    all_obs_list.append(obs_val)
                    
                    # Category count
                    if i < len(cat_cols):
                        cat_col = cat_cols[i]
                        cat_val = str(row[cat_col]).strip() if cat_col in row and pd.notna(row[cat_col]) else "Other"
                        if cat_val and cat_val.lower() != "nan":
                            category_counts[cat_val] = category_counts.get(cat_val, 0) + 1
                    
                    # Severity count
                    if i < len(sev_cols):
                        sev_col = sev_cols[i]
                        try:
                            sev_val = float(row[sev_col])
                            if sev_val in [4.0, 5.0]:
                                critical_observations += 1
                                all_crit_obs_list.append(obs_val)
                        except:
                            pass
            
            # Contractor violations
            if row_obs_count > 0:
                contractor_obs[contractor] = contractor_obs.get(contractor, 0) + row_obs_count
                
        # 4. High Risk Permits
        risk_col = [c for c in df_ptw.columns if "risk" in c.lower()]
        if risk_col:
            df_hr = df_ptw[df_ptw[risk_col[0]].astype(str).str.lower().str.contains("high")]
            high_risk_issued = len(df_hr)
            high_risk_safely_executed = df_hr['Completion time'].notna().sum() if 'Completion time' in df_hr.columns else high_risk_issued
            
            # High risk observations
            df_joined = pd.merge(df_audit, df_ptw[['PTW No', risk_col[0]]], on='PTW No', how='inner')
            df_hr_audit = df_joined[df_joined[risk_col[0]].astype(str).str.lower().str.contains("high")]
            high_risk_observations = 0
            for obs_col in obs_cols:
                if obs_col in df_hr_audit.columns:
                    high_risk_observations += df_hr_audit[obs_col].dropna().astype(str).str.strip().str.lower().apply(
                        lambda x: x not in ["", "nan", "none", "nil"]
                    ).sum()
        else:
            high_risk_issued = int(0.15 * total_issued)
            high_risk_safely_executed = high_risk_issued
            high_risk_observations = int(0.1 * total_observations)
            
        # 5. Top Violators (Contractors)
        sorted_violators = sorted(contractor_obs.items(), key=lambda x: x[1], reverse=True)
        violators = [[i, name, count] for i, (name, count) in enumerate(sorted_violators[:3], 1)]
        top3_obs_sum = sum(count for _, _, count in violators)
        violators_contrib = int(top3_obs_sum / total_observations * 100) if total_observations > 0 else 0
        
        # 6. Categories of Violations
        sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
        categories = [[i, cat_name, count] for i, (cat_name, count) in enumerate(sorted_categories[:4], 1)]
        
        # 7. Top High Risk/Critical Observations
        # Count frequency of critical observations or general observations if no critical ones
        obs_to_count = all_crit_obs_list if all_crit_obs_list else all_obs_list
        obs_freq = {}
        for o in obs_to_count:
            # simple fuzzy match grouping by prefix
            prefix = o[:70]
            obs_freq[prefix] = obs_freq.get(prefix, 0) + 1
            
        sorted_hr_obs = sorted(obs_freq.items(), key=lambda x: x[1], reverse=True)
        high_risk_obs = [[i, text, count] for i, (text, count) in enumerate(sorted_hr_obs[:3], 1)]
        
        # Calculate Compliance
        compliance = max(0, int((total_issued - total_observations) / total_issued * 100)) if total_issued > 0 else 100
        
        return {
            'total_issued': total_issued,
            'total_closed': total_closed,
            'total_audited': total_audited,
            'total_observations': total_observations,
            'critical_observations': critical_observations,
            'compliance': compliance,
            'compliance_donut': compliance,
            'high_risk_issued': high_risk_issued,
            'high_risk_safely_executed': high_risk_safely_executed,
            'high_risk_observations': high_risk_observations,
            'violators': violators if violators else [[1, 'None', 0]],
            'violators_contrib': violators_contrib,
            'high_risk_obs': high_risk_obs if high_risk_obs else [[1, 'None', 0]],
            'categories': categories if categories else [[1, 'None', 0]]
        }
    except Exception as e:
        logger.error(f"Error computing dynamic PTW metrics: {e}")
        return STATIC_PTW

# --- Main Render ---
def render_ptw_dashboard():
    # Render Data Source Selector in Sidebar (Toggled local file uploader button)
    source_type = render_source_selector("ptw")
    
    config = load_config()
    current_ptw_path = config.get("ptw_path", DEFAULT_PTW_PATH)
    current_ptw_audit_path = config.get("ptw_audit_path", DEFAULT_PTW_AUDIT_PATH)
    
    path_exists = True
    ptw_source_file = None
    loaded_precalculated = False
    
    if source_type == "aws":
        aws_ptw = os.path.join(S3_CACHE_DIR, "PTW 1.xlsx")
        aws_audit = os.path.join(S3_CACHE_DIR, "PTW 1.xlsx")
        if not os.path.exists(aws_ptw):
            aws_ptw = os.path.join(S3_CACHE_DIR, "PTW.xlsx")
            aws_audit = os.path.join(S3_CACHE_DIR, "PTW Audit.xlsx")
            
        df_ptw, df_audit = load_ptw_data(aws_ptw, aws_audit)
        path_exists = os.path.exists(aws_ptw) or (os.path.exists(aws_ptw) and os.path.exists(aws_audit))
        ptw_source_file = aws_ptw if path_exists else None
        
    else:  # upload mode - fetch uploaded file from session state
        uploaded_ptw = st.session_state.get("ptw_file")
        if uploaded_ptw is not None:
            df_ptw, df_audit = load_ptw_data(uploaded_ptw, uploaded_ptw)
            path_exists = True
            ptw_source_file = uploaded_ptw
        else:
            df_ptw, df_audit = pd.DataFrame(), pd.DataFrame()
            path_exists = False
            ptw_source_file = None

    st.sidebar.markdown("<hr style='border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
    st.sidebar.markdown("<h2 style='text-align: center; color: white;'>⚙️ CONTROLS</h2>", unsafe_allow_html=True)

    if st.sidebar.button("🔄 Refresh PTW Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    # Load metrics: try precalculated first, fallback to compute_ptw_metrics
    metrics = None
    if ptw_source_file:
        metrics = load_precalculated_ptw_metrics(ptw_source_file)
        if metrics is not None:
            loaded_precalculated = True
            
    if metrics is None:
        metrics = compute_ptw_metrics(df_ptw, df_audit)

    # Connection Status indicator in sidebar
    if path_exists and (loaded_precalculated or not df_ptw.empty):
        if loaded_precalculated:
            st.sidebar.success(f"✅ Excel Connected!\nLoaded pre-calculated data\nParsed PTW ({len(df_ptw)} entries)\nParsed Audits ({len(df_audit)} entries)")
        else:
            st.sidebar.success(f"✅ Excel Connected!\nParsed PTW ({len(df_ptw)} entries)\nParsed Audits ({len(df_audit)} entries)")
    else:
        st.sidebar.warning("⚠️ Excel Files Not Connected!")

    date_display_str = "Q2 FY26"
    
    header_html = f"""
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
    """
    render_html(header_html)

    if source_type == "aws" and not path_exists:
        st.warning("⚠️ AWS S3 local cache not found. Please click '☁️ Sync AWS' first in the sidebar to sync your files.")
        return
    elif source_type == "upload" and not path_exists:
        st.warning("⚠️ Please upload PTW 1 Excel file in the sidebar to render the dashboard.")
        return
    
    # ── KPI Row 1 (Beautified to match CSFA) ──────────────────────────────────
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        render_kpi_metric("No. Of work permits issued", "📋", f"{metrics['total_issued']:,}", "#0033a0", "#eef2ff", "#bfdbfe")
    with col2:
        render_kpi_metric("No. Of work permits closed", "✅", f"{metrics['total_closed']:,}", "#27ae60", "#f0fdf4", "#bbf7d0")
    with col3:
        render_kpi_metric("No. Of Work permits Audited", "🔍", f"{metrics['total_audited']:,}", "#8e24aa", "#faf5ff", "#e9d5ff")
    with col4:
        render_kpi_metric("No. Of observations", "💬", f"{metrics['total_observations']:,}", "#e67e22", "#fff7ed", "#ffedd5")
    with col5:
        render_kpi_metric("Critical Observations", "⚠️", f"{metrics['critical_observations']:,}", "#fa5252", "#fff5f5", "#fca5a5")
    with col6:
        render_kpi_metric("Compliance", "📊", f"{metrics['compliance']:.0f}%", "#10b981", "#ecfdf5", "#a7f3d0")
            
    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
            
    # ── KPI Row 2 (Balanced to fill the entire row width) ─────────────────────
    row2_col1, row2_col2, row2_col3 = st.columns(3)
    with row2_col1:
        render_kpi_metric("No. of high Risk permits issued", "👷", f"{metrics['high_risk_issued']:,}", "#0f766e", "#f0fdfa", "#99f6e4")
    with row2_col2:
        render_kpi_metric("High Risk permits Safely Executed", "✅", f"{metrics['high_risk_safely_executed']:,}", "#27ae60", "#f0fdf4", "#bbf7d0")
    with row2_col3:
        render_kpi_metric("No. Of Observations in High-Risk permits", "❗", f"{metrics['high_risk_observations']:,}", "#e11d48", "#fff5f5", "#fca5a5")
            
    st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
            
    # ── Grid Row 3 ────────────────────────────────────────────────────────────
    left_col, right_col = st.columns([1, 1.2])
    
    with left_col:
        # Compliance donut card
        with st.container(border=True):
            st.markdown("<h4 style='margin:0; padding-bottom:8px; border-bottom:2px solid #0033a0; color:#002060; font-weight:900; font-size:16.5px; text-transform:uppercase;'>🎯 COMPLIANCE</h4>", unsafe_allow_html=True)
            
            c_col1, c_col2 = st.columns([1, 1])
            with c_col1:
                fig_donut = render_donut_chart(metrics['compliance_donut'])
                st.plotly_chart(fig_donut, use_container_width=True, config={'displayModeBar': False})
            with c_col2:
                formula_html = f"""
                <div style="display: flex; flex-direction: column; justify-content: center; height: 180px; padding-left: 10px; font-family: 'Inter', sans-serif;">
                    <div style="font-size: 13.5px; color: #1e293b; margin-bottom: 8px; font-weight: 800;">Compliance is calculated as:</div>
                    <div style="display: flex; align-items: center; font-size: 16px; font-weight: 900; color: #002256;">
                        <div style="display: flex; flex-direction: column; align-items: center; margin-right: 8px;">
                            <div style="border-bottom: 2px solid #002256; padding-bottom: 4px; text-align: center; width: 100%;">
                                {metrics['total_issued']} - {metrics['total_observations']}
                            </div>
                            <div style="padding-top: 4px; text-align: center; width: 100%;">
                                {metrics['total_issued']}
                            </div>
                        </div>
                        <div style="font-size: 18.5px; font-weight: 900; margin-left: 5px;">× 100</div>
                    </div>
                </div>
                """
                render_html(formula_html)
        
        # Top Violators table
        violator_title = f"TOP 3 VIOLATORS – CONTRIBUTING {metrics['violators_contrib']}%"
        violators_html = generate_html_table(
            violator_title,
            ["#", "CONTRACTOR", "NO. OF OBSERVATIONS"],
            pad_rows_to_three(metrics['violators'][:3])
        )
        render_html(violators_html)
        
    with right_col:
        # Top High Risk Observations table
        hr_obs_html = generate_html_table(
            "TOP 3 HIGH RISK OBSERVATIONS",
            ["#", "OBSERVATION", "NO. OF OCCURRENCES"],
            pad_rows_to_three(metrics['high_risk_obs'][:3])
        )
        render_html(hr_obs_html)
        
        # Categories of Violation table
        categories_html = generate_html_table(
            "CATEGORIES OF VIOLATION",
            ["#", "CATEGORY", "NO. OF OBSERVATIONS"],
            pad_rows_to_three(metrics['categories'][:3])
        )
        render_html(categories_html)
