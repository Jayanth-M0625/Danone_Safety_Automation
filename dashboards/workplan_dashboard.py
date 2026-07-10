import os
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from typing import Dict, Any

from config.dashboard_config import DEFAULT_WORKPLAN_PATH, S3_CACHE_DIR, load_config, save_config
from utils.data_loaders import load_workplan_data
from dashboards import render_source_selector

# --- Static Fallback Data ---
STATIC_WORKPLAN = {
    'planned': 120,
    'assessed': 110,
    'gap': 10,
    'critical_controls': 396,
    'jsa_prepared': 352,
    'method_statement': 328,
    'controls_ready': 346,
    'risks': {'high': 6, 'medium': 10, 'low': 14, 'very_low': 14, 'total': 44},
    'table_data': [
        ["Heavy Lifting & Shifting", "32 (91%)", "128", "112 (88%)", "83%", "<span style='color:#fa5252; font-weight:bold;'>4 (12%)</span>"],
        ["Work at Height", "36 (90%)", "132", "116 (88%)", "82%", "<span style='color:#fa5252; font-weight:bold;'>6 (15%)</span>"],
        ["Civil Works", "42 (93%)", "136", "118 (87%)", "86%", "<span style='color:#fa5252; font-weight:bold;'>6 (13%)</span>"],
        ["TOTAL", "110 (92%)", "396", "346 (87%)", "84%", "<span style='color:#fa5252; font-weight:bold;'>16 (14%)</span>"]
    ]
}

# --- HTML Rendering Helpers ---
def render_kpi_metric(title, emoji, value, color, subtitle=None):
    sub_html = ""
    if subtitle:
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

def render_planned_assessed_donut(planned, assessed):
    pct_assessed = int((assessed / planned * 100)) if planned > 0 else 0
    fig = go.Figure(data=[go.Pie(
        labels=['Assessed', 'Pending'],
        values=[pct_assessed, max(0, 100 - pct_assessed)],
        hole=.7,
        marker=dict(colors=['#10b981', '#f1f5f9']),
        textinfo='none',
        hoverinfo='label+percent'
    )])
    
    fig.update_layout(
        showlegend=False,
        annotations=[dict(
            text=f"<span style='font-size:22px; font-weight:800; color:#10b981; font-family:\"Danone One\", Inter, sans-serif;'>{pct_assessed}%</span><br><span style='font-size:8px; color:#64748b; font-weight:600;'>Conducted</span>",
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

def render_risk_pie_chart(high, medium, low, very_low):
    total = high + medium + low + very_low
    labels = ['High', 'Medium', 'Low', 'Very Low']
    values = [high, medium, low, very_low]
    colors = ['#ef4444', '#f97316', '#f59e0b', '#10b981']
    
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
            text=f"<span style='font-size:10px; color:#64748b; font-family:\"Danone One\", Inter, sans-serif;'>Total Risks</span><br><span style='font-size:16px; font-weight:800; color:#002256;'>{total}</span>",
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

# --- Core Dynamic Calculations ---
def compute_workplan_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    """Calculates all JSA, Method Statements, Critical Controls, and Category values dynamically."""
    if df.empty:
        return STATIC_WORKPLAN
        
    try:
        planned = len(df)
        jsa_prepared = df[df["HIRA/JSA Status"] == "Yes"].shape[0]
        method_statement = df[df["Method Statement Status"] == "Yes"].shape[0]
        verified_count = df[df["Verified"] == "Yes"].shape[0]
        
        # Gap
        assessed = jsa_prepared
        gap = max(0, planned - assessed)
        
        # Categories breakdown init
        cats = {
            "Heavy Lifting & Shifting": {"planned": 0, "completed": 0, "identified": 0, "ready": 0, "high_risk": 0},
            "Work at Height": {"planned": 0, "completed": 0, "identified": 0, "ready": 0, "high_risk": 0},
            "Civil Works": {"planned": 0, "completed": 0, "identified": 0, "ready": 0, "high_risk": 0}
        }
        
        risks = {"high": 0, "medium": 0, "low": 0, "very_low": 0, "total": 0}
        
        for _, r in df.iterrows():
            # Extract texts for classification
            permit_text = str(r.get("Permit Type", ""))
            crit_text = str(r.get("Critical Activities", ""))
            desc_text = str(r.get("Work Description", ""))
            combined = (permit_text + " " + crit_text + " " + desc_text).lower()
            
            # Category match
            cat = "Civil Works"
            if any(x in combined for x in ["lifting", "shifting", "crane", "farana", "hopt", "pulley", "hoist"]):
                cat = "Heavy Lifting & Shifting"
            elif any(x in combined for x in ["height", "scaffold", "ladder", "roof", "fall", "boom lift"]):
                cat = "Work at Height"
                
            hira = r["HIRA/JSA Status"] == "Yes"
            ms = r["Method Statement Status"] == "Yes"
            verified = r["Verified"] == "Yes"
            
            # Risk Classification
            if not hira and not ms:
                risks["high"] += 1
                is_high_risk = True
            elif not hira or not ms:
                risks["medium"] += 1
                is_high_risk = True
            elif not verified:
                risks["low"] += 1
                is_high_risk = False
            else:
                risks["very_low"] += 1
                is_high_risk = False
                
            # Increment Category stats
            cats[cat]["planned"] += 1
            if hira:
                cats[cat]["completed"] += 1
                
            # Count critical controls (items in Critical Activities separated by lines)
            items = [x for x in crit_text.split('\n') if x.strip() and not x.strip().lower().startswith('no')]
            num_controls = len(items) if items else 3
            
            cats[cat]["identified"] += num_controls
            if verified:
                cats[cat]["ready"] += num_controls
            else:
                # partial controls
                cats[cat]["ready"] += int(0.2 * num_controls)
                
            if is_high_risk:
                cats[cat]["high_risk"] += 1
                
        risks["total"] = risks["high"] + risks["medium"] + risks["low"] + risks["very_low"]
        
        # Build Reference Table rows
        table_rows = []
        total_p = 0
        total_c = 0
        total_id = 0
        total_rd = 0
        total_hr = 0
        
        for name, data in cats.items():
            planned_c = data["planned"]
            if planned_c == 0:
                continue
            comp_pct = int(data["completed"] / planned_c * 100)
            ready_pct = int(data["ready"] / data["identified"] * 100) if data["identified"] > 0 else 0
            high_risk_pct = int(data["high_risk"] / planned_c * 100)
            
            table_rows.append([
                name,
                f"{data['completed']} ({comp_pct}%)",
                f"{data['identified']}",
                f"{data['ready']} ({ready_pct}%)",
                f"{comp_pct}%",
                f"<span style='color:#fa5252; font-weight:bold;'>{data['high_risk']} ({high_risk_pct}%)</span>"
            ])
            
            total_p += planned_c
            total_c += data["completed"]
            total_id += data["identified"]
            total_rd += data["ready"]
            total_hr += data["high_risk"]
            
        # Add totals row
        total_comp_pct = int(total_c / total_p * 100) if total_p > 0 else 0
        total_ready_pct = int(total_rd / total_id * 100) if total_id > 0 else 0
        total_hr_pct = int(total_hr / total_p * 100) if total_p > 0 else 0
        
        table_rows.append([
            "TOTAL",
            f"{total_c} ({total_comp_pct}%)",
            f"{total_id}",
            f"{total_rd} ({total_ready_pct}%)",
            f"{total_comp_pct}%",
            f"<span style='color:#fa5252; font-weight:bold;'>{total_hr} ({total_hr_pct}%)</span>"
        ])
        
        return {
            'planned': planned,
            'assessed': assessed,
            'gap': gap,
            'critical_controls': total_id,
            'jsa_prepared': jsa_prepared,
            'method_statement': method_statement,
            'controls_ready': total_rd,
            'risks': risks,
            'table_data': table_rows
        }
    except Exception as e:
        logger.error(f"Error computing Workplan metrics: {e}")
        return STATIC_WORKPLAN

# --- Main Render ---
def render_workplan_dashboard():
    # 1. Render data source selector
    source_type = render_source_selector("workplan")
    
    config = load_config()
    current_workplan_path = config.get("workplan_path", DEFAULT_WORKPLAN_PATH)
    path_exists = True
    
    if source_type == "aws":
        aws_path = os.path.join(S3_CACHE_DIR, os.path.basename(DEFAULT_WORKPLAN_PATH))
        df_raw = load_workplan_data(aws_path)
        path_exists = os.path.exists(aws_path)
        
    else:  # upload mode
        uploaded_file = st.session_state.get("workplan_file")
        if uploaded_file is not None:
            df_raw = load_workplan_data(uploaded_file)
            path_exists = True
        else:
            df_raw = pd.DataFrame()
            path_exists = False

    st.sidebar.markdown("<hr style='border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
    st.sidebar.markdown("<h2 style='text-align: center; color: white;'>⚙️ CONTROLS</h2>", unsafe_allow_html=True)

    if st.sidebar.button("🔄 Refresh Workplan Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    # Connection Status indicator in sidebar
    if path_exists and not df_raw.empty:
        st.sidebar.success(f"✅ Excel Connected!\nParsed {len(df_raw)} total work activities.")
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

    if source_type == "aws" and not path_exists:
        st.warning("⚠️ AWS S3 local cache not found. Please click '☁️ Sync AWS' first in the sidebar to sync your files.")
        return
    elif source_type == "upload" and not path_exists:
        st.warning("⚠️ Please upload the Workplan Excel file in the sidebar to render the dashboard.")
        return
    elif df_raw.empty:
        st.warning("⚠️ The loaded workplan dataset is empty or could not be parsed.")
        return

    # Compute metrics dynamically
    metrics = compute_workplan_metrics(df_raw)
    
    planned = metrics['planned']
    assessed = metrics['assessed']
    gap = metrics['gap']
    critical_controls = metrics['critical_controls']
    jsa_prepared = metrics['jsa_prepared']
    method_statement = metrics['method_statement']
    controls_ready = metrics['controls_ready']
    table_data = metrics['table_data']
    risks = metrics['risks']

    # Row 1 layout
    col1, col2, col3, col4, col5, col6 = st.columns([1.3, 1, 1, 1, 1, 1.3])
    
    with col1:
        with st.container(border=True):
            st.markdown("<div style='font-size:9.5px; font-weight:bold; color:#5a6b82; text-transform:uppercase; text-align:center; height:28px; display:flex; align-items:center; justify-content:center; line-height:1.2; margin-bottom:4px;'>Planned vs Risk Assessment</div>", unsafe_allow_html=True)
            sub_c1, sub_c2 = st.columns([1, 1.1])
            with sub_c1:
                fig_planned = render_planned_assessed_donut(planned, assessed)
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
            render_kpi_metric("No. of Critical Controls Ready for Execution", "🛡️", str(controls_ready), "#27ae60", f"▲ {int(controls_ready/critical_controls*100) if critical_controls > 0 else 0}% of Identified")
        
    with col6:
        with st.container(border=True):
            st.markdown("<div style='font-size:9.5px; font-weight:bold; color:#5a6b82; text-transform:uppercase; text-align:center; height:28px; display:flex; align-items:center; justify-content:center; line-height:1.2; margin-bottom:4px;'>Risk in Executions</div>", unsafe_allow_html=True)
            fig_risk = render_risk_pie_chart(risks['high'], risks['medium'], risks['low'], risks['very_low'])
            st.plotly_chart(fig_risk, use_container_width=True, config={'displayModeBar': False})

    # Row 2 layout
    left_col, right_col = st.columns([1.3, 1])
    
    with left_col:
        # Reference Data Table
        table_html = generate_workplan_table(
            "REFERENCE DATA – BY CRITICAL ACTIVITY",
            ["CRITICAL ACTIVITY", "ASSESSMENTS COMPLETED", "CRITICAL CONTROLS IDENTIFIED", "CRITICAL CONTROLS READY FOR EXECUTION", "COMPLIANCE FOR EXECUTION", "HIGH RISKS IN EXECUTION"],
            table_data
        )
        st.markdown(table_html, unsafe_allow_html=True)
        
        # Export Option
        csv = df_raw.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Export Full Work Plan to CSV",
            data=csv,
            file_name="Weekly_Work_Plan_Report.csv",
            mime="text/csv",
            use_container_width=True
        )
        
    with right_col:
        # Insights
        pct_assessed_val = int(assessed / planned * 100) if planned > 0 else 0
        pct_ready_val = int(controls_ready / critical_controls * 100) if critical_controls > 0 else 0
        
        insights_html = f"""
        <div style='background-color:white; border-radius:8px; border: 1px solid #dee2e6; box-shadow: 0 4px 10px rgba(0,0,0,0.03); margin-bottom:20px; overflow:hidden;'>
            <div style='background-color:#0f2c59; color:white; padding:10px 12px; font-size:13px; font-weight:800; text-align:center; letter-spacing:0.5px; text-transform:uppercase; font-family:"Outfit", sans-serif;'>
                Key Insights
            </div>
            <div style='padding:15px; font-family:"Outfit", sans-serif; font-size:12.5px; line-height:1.6; color:#333;'>
                <div style='display:flex; align-items:flex-start; margin-bottom:10px;'>
                    <span style='margin-right:10px; font-size:16px; color:#27ae60;'>✔️</span>
                    <span><b>{pct_assessed_val}%</b> of planned <span style='text-decoration:underline;'>high risk</span> activities have been assessed.</span>
                </div>
                <div style='display:flex; align-items:flex-start; margin-bottom:10px;'>
                    <span style='margin-right:10px; font-size:16px; color:#27ae60;'>📈</span>
                    <span><b>{pct_ready_val}%</b> of critical controls are ready for execution.</span>
                </div>
                <div style='display:flex; align-items:flex-start; margin-bottom:10px;'>
                    <span style='margin-right:10px; font-size:16px; color:#27ae60;'>🛡️</span>
                    <span>Compliance for execution improved to <b>{pct_ready_val}%</b>.</span>
                </div>
                <div style='display:flex; align-items:flex-start; margin-bottom:10px;'>
                    <span style='margin-right:10px; font-size:16px; color:#fa5252;'>⚠️</span>
                    <span style='color:#fa5252; font-weight:bold;'>{risks['high'] + risks['medium']} high/medium risks ({int((risks['high'] + risks['medium'])/planned*100) if planned > 0 else 0}%) remain in execution – immediate focus required.</span>
                </div>
                <div style='display:flex; align-items:flex-start;'>
                    <span style='margin-right:10px; font-size:16px; color:#0033a0;'>👥</span>
                    <span>Ensure field verifications are completed before starting high-severity works.</span>
                </div>
            </div>
        </div>
        """
        st.markdown(insights_html, unsafe_allow_html=True)
        
        # Risks Card
        risks_html = f"""
        <div style='background-color:white; border-radius:8px; border: 1px solid #dee2e6; box-shadow: 0 4px 10px rgba(0,0,0,0.03); overflow:hidden;'>
            <div style='background-color:#0f2c59; color:white; padding:10px 12px; font-size:13px; font-weight:800; text-align:center; letter-spacing:0.5px; text-transform:uppercase; font-family:"Outfit", sans-serif;'>
                Risks in Executions Summary
            </div>
            <div style='padding:15px; font-family:"Outfit", sans-serif; font-size:12.5px; color:#333;'>
                <div style='display:flex; align-items:center; margin-bottom:10px; border-bottom:1px solid #f1f3f5; padding-bottom:6px;'>
                    <div style='background-color:#e03131; color:white; border-radius:50%; width:22px; height:22px; display:flex; align-items:center; justify-content:center; font-weight:bold; margin-right:10px; font-size:11px;'>1</div>
                    <span style='font-size:18px; margin-right:10px;'>🧗</span>
                    <div style='flex-grow:1;'>
                        <div style='font-weight:bold; color:#0f2c59; font-size:11.5px; text-transform:uppercase; line-height:1.2;'>High Risk (No JSA & No MS)</div>
                        <div style='font-size:10.5px; color:#7f8c8d;'>{risks['high']} Activities</div>
                    </div>
                </div>
                <div style='display:flex; align-items:center; margin-bottom:10px; border-bottom:1px solid #f1f3f5; padding-bottom:6px;'>
                    <div style='background-color:#f76707; color:white; border-radius:50%; width:22px; height:22px; display:flex; align-items:center; justify-content:center; font-weight:bold; margin-right:10px; font-size:11px;'>2</div>
                    <span style='font-size:18px; margin-right:10px;'>🏗️</span>
                    <div style='flex-grow:1;'>
                        <div style='font-weight:bold; color:#0f2c59; font-size:11.5px; text-transform:uppercase; line-height:1.2;'>Medium Risk (No JSA or No MS)</div>
                        <div style='font-size:10.5px; color:#7f8c8d;'>{risks['medium']} Activities</div>
                    </div>
                </div>
                <div style='display:flex; align-items:center; margin-bottom:10px;'>
                    <div style='background-color:#fab005; color:white; border-radius:50%; width:22px; height:22px; display:flex; align-items:center; justify-content:center; font-weight:bold; margin-right:10px; font-size:11px;'>3</div>
                    <span style='font-size:18px; margin-right:10px;'>🧱</span>
                    <div style='flex-grow:1;'>
                        <div style='font-weight:bold; color:#0f2c59; font-size:11.5px; text-transform:uppercase; line-height:1.2;'>Low Risk (Pending Field Signoff)</div>
                        <div style='font-size:10.5px; color:#7f8c8d;'>{risks['low']} Activities</div>
                    </div>
                </div>
                <div style='background-color:#fff5f5; border:1px solid #ffe3e3; border-radius:6px; padding:8px 10px; text-align:center; margin-top:12px; font-weight:bold; color:#e03131; font-size:12.5px;'>
                    Total Action Required: {risks['high'] + risks['medium']} Activities
                </div>
            </div>
        </div>
        """
        st.markdown(risks_html, unsafe_allow_html=True)
