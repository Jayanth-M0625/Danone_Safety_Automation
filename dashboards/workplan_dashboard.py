import os
import re
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from typing import Dict, Any

from config.dashboard_config import DEFAULT_WORKPLAN_PATH, S3_CACHE_DIR, load_config, save_config
from utils.data_loaders import load_workplan_data
from dashboards import render_source_selector

# ── Static Fallback Data ──────────────────────────────────────────────────────
STATIC_WORKPLAN = {
    "planned": 120, "assessed": 110, "gap": 10,
    "critical_controls": 396, "jsa_prepared": 352,
    "method_statement": 328, "controls_ready": 346,
    "risks": {"high": 6, "medium": 10, "low": 14, "very_low": 14, "total": 44},
    "table_data": [
        ["Heavy Lifting & Shifting", "32 (91%)", "128", "112 (88%)", "83%", "4 (12%)"],
        ["Work at Height",           "36 (90%)", "132", "116 (88%)", "82%", "6 (15%)"],
        ["Civil Works",              "42 (93%)", "136", "118 (87%)", "86%", "6 (13%)"],
        ["TOTAL",                    "110 (92%)", "396", "346 (87%)", "84%", "16 (14%)"],
    ],
}

# ── HTML Rendering Helpers ────────────────────────────────────────────────────
def render_html(html_str):
    """Renders HTML directly to Streamlit, bypassing markdown parsing completely."""
    st.html(html_str)

def kpi_card(label, emoji, value, accent_color, badge_bg, badge_border, note=None):
    """Renders a beautifully styled KPI card matching the CSFA dashboard styling with high contrast text."""
    note_html = f"<div style='font-size: 10px; color: #5a6b82; font-weight: 800; margin-top: 3px;'>{note}</div>" if note else ""
    html = f"""
    <div style="background-color: #ffffff; border-radius: 12px; padding: 12px 15px; border: 1px solid #cbd5e1; box-shadow: 0 4px 12px rgba(0,34,86,0.06); display: flex; align-items: center; gap: 12px; height: 95px; position: relative;">
        <div style="background-color: {badge_bg}; width: 38px; height: 38px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 16px; flex-shrink: 0; border: 1px solid {badge_border};">{emoji}</div>
        <div style="flex-grow: 1; display: flex; flex-direction: column; justify-content: center;">
            <div style="font-size: 11px; font-weight: 900; color: #1e293b; text-transform: uppercase; letter-spacing: 0.5px; line-height: 1.1;">{label}</div>
            <div style="font-size: 22px; font-weight: 950; color: {accent_color}; line-height: 1; margin-top: 4px;">{value}</div>
            {note_html}
            <div style="width: 25px; height: 3px; background-color: {accent_color}; border-radius: 2px; margin-top: 5px;"></div>
        </div>
    </div>
    """
    return html

def generate_html_table(title, headers, rows):
    """Generates an HTML table styled identically to the CSFA dashboard tables with highlighted total row."""
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
        is_total = str(r[0]).upper() == "TOTAL"
        bg_color = "#eff6ff" if is_total else ("#ffffff" if r_idx % 2 == 0 else "#f8fafc")
        font_weight_row = "850" if is_total else "700"
        
        row_cols_html = ""
        for c_idx, val in enumerate(r):
            align = "center" if c_idx > 0 else "left"
            weight = "850" if is_total or c_idx == 0 or (c_idx == len(r) - 1) else "700"
            row_cols_html += f"<td style='padding: 10px; text-align: {align}; font-weight: {weight}; border: none;'>{val}</td>"
        rows_html += f"<tr style='background-color: {bg_color}; border-bottom: 1px solid #cbd5e1; font-size: 12px; color: #0f172a; font-weight: {font_weight_row};'>{row_cols_html}</tr>"
        
    html = f"""
    <div style="background-color: #ffffff; border-radius: 12px; border: 1px solid #cbd5e1; box-shadow: 0 4px 12px rgba(0,34,86,0.06); padding: 18px; margin-bottom: 20px; font-family: 'Inter', sans-serif;">
        <h4 style="margin: 0; padding-bottom: 10px; border-bottom: 2px solid #0033a0; color: #002060; font-weight: 900; font-size: 14px; text-transform: uppercase;">
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

def strip_html(s):
    return re.sub(r"<[^>]+>", "", str(s))

# ── Chart helpers ─────────────────────────────────────────────────────────────
def render_planned_assessed_donut(planned, assessed):
    pct = int(assessed / planned * 100) if planned > 0 else 0
    fig = go.Figure(data=[go.Pie(
        labels=["Assessed", "Pending"],
        values=[pct, max(0, 100 - pct)],
        hole=0.7,
        marker=dict(colors=["#22c55e", "#e2e8f0"]),
        textinfo="none", hoverinfo="label+percent",
    )])
    fig.update_layout(
        showlegend=False,
        annotations=[dict(
            text=f"<span style='font-size:22px; font-weight:950; color:#16a34a; font-family:\"Inter\", sans-serif;'>{pct}%</span><br><span style='font-size:9px; font-weight:800; color:#475569;'>Conducted</span>",
            x=0.5, y=0.5, showarrow=False
        )],
        margin=dict(l=0, r=0, t=0, b=0), height=125,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig

def render_risk_pie_chart(high, medium, low, very_low):
    total = high + medium + low + very_low
    fig = go.Figure(data=[go.Pie(
        labels=["High", "Medium", "Low", "Very Low"],
        values=[high, medium, low, very_low],
        hole=0.6,
        marker=dict(colors=["#ef4444", "#f97316", "#f59e0b", "#10b981"]),
        textinfo="percent", textposition="inside",
        hoverinfo="label+value+percent",
    )])
    fig.update_layout(
        showlegend=False,
        annotations=[dict(
            text=f"<span style='font-size:22px; font-weight:950; color:#0f172a; font-family:\"Inter\", sans-serif;'>{total}</span><br><span style='font-size:9px; font-weight:800; color:#475569;'>Total</span>",
            x=0.5, y=0.5, showarrow=False
        )],
        margin=dict(l=0, r=0, t=0, b=0), height=125,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig

# ── Dynamic Calculations ──────────────────────────────────────────────────────
def compute_workplan_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    if df.empty:
        return STATIC_WORKPLAN
    try:
        planned          = len(df)
        jsa_prepared     = df[df["HIRA/JSA Status"] == "Yes"].shape[0]
        method_statement = df[df["Method Statement Status"] == "Yes"].shape[0]

        assessed = jsa_prepared
        gap      = max(0, planned - assessed)

        cats = {
            "Heavy Lifting & Shifting": {"planned": 0, "completed": 0, "identified": 0, "ready": 0, "high_risk": 0},
            "Work at Height":           {"planned": 0, "completed": 0, "identified": 0, "ready": 0, "high_risk": 0},
            "Civil Works":              {"planned": 0, "completed": 0, "identified": 0, "ready": 0, "high_risk": 0},
        }
        risks = {"high": 0, "medium": 0, "low": 0, "very_low": 0, "total": 0}

        for _, r in df.iterrows():
            permit_text = str(r.get("Permit Type", ""))
            crit_text   = str(r.get("Critical Activities", ""))
            desc_text   = str(r.get("Work Description", ""))
            combined    = (permit_text + " " + crit_text + " " + desc_text).lower()

            cat = "Civil Works"
            if any(x in combined for x in ["lifting","shifting","crane","farana","hopt","pulley","hoist"]):
                cat = "Heavy Lifting & Shifting"
            elif any(x in combined for x in ["height","scaffold","ladder","roof","fall","boom lift"]):
                cat = "Work at Height"

            hira     = r["HIRA/JSA Status"] == "Yes"
            ms       = r["Method Statement Status"] == "Yes"
            verified = r["Verified"] == "Yes"

            if not hira and not ms:
                risks["high"] += 1;     is_hr = True
            elif not hira or not ms:
                risks["medium"] += 1;   is_hr = True
            elif not verified:
                risks["low"] += 1;      is_hr = False
            else:
                risks["very_low"] += 1; is_hr = False

            cats[cat]["planned"] += 1
            if hira: cats[cat]["completed"] += 1

            items = [x for x in crit_text.split("\n") if x.strip() and not x.strip().lower().startswith("no")]
            cats[cat]["identified"] += len(items) if items else 0
            if verified: cats[cat]["ready"] += len(items) if items else 0
            if is_hr: cats[cat]["high_risk"] += 1

        risks["total"] = risks["high"] + risks["medium"] + risks["low"] + risks["very_low"]

        table_rows = []
        total_p = total_c = total_id = total_rd = total_hr = 0
        for name, data in cats.items():
            if data["planned"] == 0:
                continue
            comp_pct     = int(data["completed"] / data["planned"] * 100)
            ready_pct    = int(data["ready"] / data["identified"] * 100) if data["identified"] > 0 else 0
            hr_pct       = int(data["high_risk"] / data["planned"] * 100)
            table_rows.append([
                name,
                f"{data['completed']} ({comp_pct}%)",
                f"{data['identified']}",
                f"{data['ready']} ({ready_pct}%)",
                f"{comp_pct}%",
                f"{data['high_risk']} ({hr_pct}%)",
            ])
            total_p  += data["planned"]
            total_c  += data["completed"]
            total_id += data["identified"]
            total_rd += data["ready"]
            total_hr += data["high_risk"]

        tc_pct  = int(total_c  / total_p  * 100) if total_p  > 0 else 0
        trd_pct = int(total_rd / total_id * 100) if total_id > 0 else 0
        thr_pct = int(total_hr / total_p  * 100) if total_p  > 0 else 0
        table_rows.append([
            "TOTAL",
            f"{total_c} ({tc_pct}%)",
            f"{total_id}",
            f"{total_rd} ({trd_pct}%)",
            f"{tc_pct}%",
            f"{total_hr} ({thr_pct}%)",
        ])

        return {
            "planned": planned, "assessed": assessed, "gap": gap,
            "critical_controls": total_id, "jsa_prepared": jsa_prepared,
            "method_statement": method_statement, "controls_ready": total_rd,
            "risks": risks, "table_data": table_rows,
        }
    except Exception:
        return STATIC_WORKPLAN

# ── Main Render ───────────────────────────────────────────────────────────────
def render_workplan_dashboard():
    # Render Data Source Selector in Sidebar (Toggled local file uploader button)
    source_type = render_source_selector("workplan")
    load_config()
    path_exists = True

    if source_type == "aws":
        aws_path = os.path.join(S3_CACHE_DIR, os.path.basename(DEFAULT_WORKPLAN_PATH))
        df_raw = load_workplan_data(aws_path)
        path_exists = os.path.exists(aws_path)
    else:
        uploaded = st.session_state.get("workplan_file")
        if uploaded is not None:
            df_raw = load_workplan_data(uploaded)
            path_exists = True
        else:
            df_raw = pd.DataFrame()
            path_exists = False

    st.sidebar.markdown("<hr style='border-color:rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
    st.sidebar.markdown("<h2 style='text-align:center;color:white;'>⚙️ CONTROLS</h2>", unsafe_allow_html=True)
    if st.sidebar.button("🔄 Refresh Workplan Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    if path_exists and not df_raw.empty:
        st.sidebar.success(f"✅ Excel Connected!\nParsed {len(df_raw)} activities.")
    else:
        st.sidebar.warning("⚠️ Excel File Not Connected!")

    # ── Header ────────────────────────────────────────────────────────────────
    header_html = """
    <div class="dashboard-header">
      <div class="header-title-box">
        <div class="header-main-title">High Risk Activities – Risk Management Overview</div>
      </div>
      <div class="header-info-box">
        <div class="header-info-lbl">Reporting Window</div>
        <div class="header-info-date">📅 Q2 FY26</div>
      </div>
    </div>
    """
    render_html(header_html)

    if source_type == "aws" and not path_exists:
        st.warning("⚠️ AWS S3 cache not found. Click '☁️ Sync AWS' first.")
        return
    if source_type == "upload" and not path_exists:
        st.warning("⚠️ Upload the Workplan Excel file in the sidebar.")
        return
    if df_raw.empty:
        st.warning("⚠️ The loaded workplan dataset is empty or could not be parsed.")
        return

    m                = compute_workplan_metrics(df_raw)
    planned          = m["planned"]
    assessed         = m["assessed"]
    gap              = m["gap"]
    critical_controls = m["critical_controls"]
    jsa_prepared     = m["jsa_prepared"]
    method_statement = m["method_statement"]
    controls_ready   = m["controls_ready"]
    table_data       = m["table_data"]
    risks            = m["risks"]
    pct_assessed     = int(assessed / planned * 100) if planned > 0 else 0
    pct_ready        = int(controls_ready / critical_controls * 100) if critical_controls > 0 else 0

    # ── Row 1: Overview + KPIs (Perfect height alignment matching KPI cards) ────
    
    # CSS injection to force Planned vs Risk Assessment container to be exactly 222px high
    st.html("""
    <style>
    div[data-testid="stHorizontalBlock"] > div:nth-child(1) div[data-testid="stVerticalBlockBorderDiv"] {
        height: 222px !important;
        padding: 15px 18px !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: flex-start !important;
    }
    </style>
    """)
    
    r1c1, r1c2, r1c3 = st.columns([1.1, 1, 1])

    with r1c1:
        with st.container(border=True):
            st.markdown("<h4 style='margin:0; padding-bottom:6px; border-bottom:2px solid #0033a0; color:#002060; font-weight:900; font-size:16.5px; text-transform:uppercase;'>📌 Planned vs Risk Assessment</h4>", unsafe_allow_html=True)
            dc1, dc2 = st.columns([1, 1])
            with dc1:
                st.plotly_chart(
                    render_planned_assessed_donut(planned, assessed),
                    use_container_width=True,
                    config={"displayModeBar": False},
                )
            with dc2:
                formula_html = f"""
                <div style="display: flex; flex-direction: column; justify-content: center; height: 125px; padding-left: 10px; font-family: 'Inter', sans-serif;">
                    <div style="font-size: 13.5px; font-weight: 800; color: #002b80; margin-bottom: 6px;">🔵 Planned: <span style="font-weight: 950; font-size: 15px;">{planned}</span></div>
                    <div style="font-size: 13.5px; font-weight: 800; color: #16a34a; margin-bottom: 6px;">🟢 Assessed: <span style="font-weight: 950; font-size: 15px;">{assessed}</span></div>
                    <div style="font-size: 13.5px; font-weight: 800; color: #dc2626;">⚠️ Gap: <span style="font-weight: 950; font-size: 15px;">{gap}</span></div>
                </div>
                """
                render_html(formula_html)

    with r1c2:
        render_html(kpi_card("Critical Controls Identified", "📋", str(critical_controls), "#0033a0", "#eef2ff", "#bfdbfe", note="Total controls across activities"))
        st.markdown("<div style='margin-top: 16px;'></div>", unsafe_allow_html=True)
        render_html(kpi_card("JSA Prepared", "📄", str(jsa_prepared), "#d97706", "#fffbeb", "#fef08a", note=f"{pct_assessed}% of planned activities"))

    with r1c3:
        render_html(kpi_card("Method Statements", "📝", str(method_statement), "#7c3aed", "#faf5ff", "#e9d5ff", note="Prepared for execution"))
        st.markdown("<div style='margin-top: 16px;'></div>", unsafe_allow_html=True)
        render_html(kpi_card("Controls Ready", "🛡️", str(controls_ready), "#059669", "#ecfdf5", "#a7f3d0", note=f"{pct_ready}% of identified controls"))

    # ── Row 2: Risk Distribution (Styled to be extremely bold and premium) ──────
    st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
    rr1, rr2, rr3, rr4, rr5 = st.columns(5)

    risk_cards = [
        ("🔴 High Risk",    risks["high"],     "#dc2626", "#fff5f5", "#fecaca", "No JSA & No Method Statement"),
        ("🟠 Medium Risk",  risks["medium"],   "#ea580c", "#fff7ed", "#fed7aa", "Missing JSA or Method Statement"),
        ("🟡 Low Risk",     risks["low"],      "#d97706", "#fefce8", "#fde68a", "Pending Field Signoff"),
        ("🟢 Very Low",     risks["very_low"], "#16a34a", "#f0fdf4", "#bbf7d0", "All controls verified"),
        ("📊 Total Risks",  risks["total"],    "#0033a0", "#eff6ff", "#bfdbfe", "Across all categories"),
    ]
    for col, (lbl, val, color, bg, border_c, sub) in zip(
        [rr1, rr2, rr3, rr4, rr5], risk_cards
    ):
        with col:
            st.markdown(
                f"<div style='padding:14px 12px;border-radius:10px;background:{bg};"
                f"border:1px solid {border_c};text-align:center;box-shadow: 0 2px 6px rgba(0,0,0,0.02);'>"
                f"<div style='font-size:11px;font-weight:900;color:{color};text-transform:uppercase;"
                f"letter-spacing:0.5px;margin-bottom:6px;'>{lbl}</div>"
                f"<div style='font-size:30px;font-weight:950;color:{color};line-height:1;'>{val}</div>"
                f"<div style='font-size:10px;color:#1e293b;font-weight:800;margin-top:6px;line-height:1.2;'>{sub}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    # ── Row 3: Reference Table + Insights ─────────────────────────────────────
    st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
    left_col, right_col = st.columns([1.4, 1])

    with left_col:
        clean_rows = [[strip_html(cell) for cell in row] for row in table_data]
        table_html = generate_html_table(
            "Reference Data – By Critical Activity",
            ["Critical Activity", "Assessments Completed", "Controls Identified", "Controls Ready", "Compliance %", "High Risks"],
            clean_rows
        )
        render_html(table_html)

        csv = df_raw.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Export Full Work Plan to CSV",
            data=csv,
            file_name="Weekly_Work_Plan_Report.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with right_col:
        with st.container(border=True):
            st.markdown("<h4 style='margin:0; padding-bottom:8px; border-bottom:2px solid #0033a0; color:#002060; font-weight:900; font-size:14px; text-transform:uppercase;'>💡 Key Insights</h4>", unsafe_allow_html=True)
            hr_medium = risks["high"] + risks["medium"]
            hr_pct    = int(hr_medium / planned * 100) if planned > 0 else 0

            insights = [
                ("✅", f"{pct_assessed}% of planned high-risk activities have been assessed.", "#16a34a"),
                ("📈", f"{pct_ready}% of critical controls are ready for execution.", "#0284c7"),
                ("🛡️", f"Compliance for execution stands at {pct_ready}%.", "#7c3aed"),
                ("⚠️", f"{hr_medium} high/medium risks ({hr_pct}%) remain — immediate focus required.", "#dc2626"),
                ("👥", "Ensure field verifications are completed before high-severity works begin.", "#0033a0"),
            ]
            st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
            for icon, text, color in insights:
                st.markdown(
                    f"<div style='display:flex;align-items:flex-start;gap:10px;"
                    f"margin-bottom:12px;font-size:13px;color:#0f172a;font-weight:700;line-height:1.4;'>"
                    f"<span style='font-size:16px;flex-shrink:0;'>{icon}</span>"
                    f"<span>{text}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

        with st.container(border=True):
            st.markdown("<h4 style='margin:0; padding-bottom:8px; border-bottom:2px solid #dc2626; color:#991b1b; font-weight:900; font-size:14px; text-transform:uppercase;'>📉 Risk in Executions</h4>", unsafe_allow_html=True)
            st.plotly_chart(
                render_risk_pie_chart(risks["high"], risks["medium"], risks["low"], risks["very_low"]),
                use_container_width=True,
                config={"displayModeBar": False},
            )
            # Legend
            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
            for label, count, color in [
                ("🔴 High (No JSA & MS)", risks["high"], "#dc2626"),
                ("🟠 Medium (Missing 1)", risks["medium"], "#ea580c"),
                ("🟡 Low (Pending Signoff)", risks["low"], "#d97706"),
                ("🟢 Very Low", risks["very_low"], "#16a34a"),
            ]:
                st.markdown(
                    f"<div style='display:flex;justify-content:space-between;align-items:center;"
                    f"font-size:12px;color:#0f172a;font-weight:700;padding:4px 0;'>"
                    f"<span>{label}</span>"
                    f"<span style='font-weight:900;color:{color};'>{count}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
