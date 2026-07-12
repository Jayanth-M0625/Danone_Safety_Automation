import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

from config.dashboard_config import DEFAULT_TOOLS_PATH, S3_CACHE_DIR, load_config, save_config
from utils.data_loaders import load_tools_data
from dashboards import render_source_selector

# ── HTML Rendering Helpers ────────────────────────────────────────────────────
def render_html(html_str):
    """Renders HTML directly to Streamlit, bypassing markdown parsing."""
    st.html(html_str)

def kpi_card(label, emoji, value, accent_color, badge_bg, badge_border, note=None):
    """Renders a beautifully styled KPI card matching the CSFA dashboard styling with high contrast text."""
    note_html = f"<div style='font-size: 10px; color: #5a6b82; font-weight: 800; margin-top: 3px;'>{note}</div>" if note else ""
    html = f"""
    <div style="background-color: #ffffff; border-radius: 12px; padding: 15px; border: 1px solid #cbd5e1; box-shadow: 0 4px 12px rgba(0,34,86,0.06); display: flex; align-items: center; gap: 12px; height: 105px; position: relative;">
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

# ── Main Render ───────────────────────────────────────────────────────────────
def render_tools_tackles_dashboard():
    # Render Data Source Selector in Sidebar (Toggled local file uploader button)
    source_type = render_source_selector("tools")
    config = load_config()
    path_exists = True

    if source_type == "aws":
        aws_path = os.path.join(S3_CACHE_DIR, os.path.basename(DEFAULT_TOOLS_PATH))
        df_raw = load_tools_data(aws_path)
        path_exists = os.path.exists(aws_path)
    else:
        uploaded_file = st.session_state.get("tools_file")
        if uploaded_file is not None:
            df_raw = load_tools_data(uploaded_file)
            path_exists = True
        else:
            df_raw = pd.DataFrame()
            path_exists = False

    st.sidebar.markdown("<hr style='border-color:rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
    st.sidebar.markdown("<h2 style='text-align:center;color:white;'>⚙️ CONTROLS</h2>", unsafe_allow_html=True)
    if st.sidebar.button("🔄 Refresh Tools Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    if path_exists and not df_raw.empty:
        st.sidebar.success(f"✅ Excel Connected!\nParsed {len(df_raw)} equipment records.")
    else:
        st.sidebar.warning("⚠️ Excel File Not Connected!")

    # ── Header ────────────────────────────────────────────────────────────────
    header_html = """
    <div class="dashboard-header">
      <div class="header-title-box">
        <div class="header-main-title">Contractor Equipment, PPE and Tools &amp; Tackles Compliance Tracker</div>
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
        st.warning("⚠️ Upload the Tools & Tackles Excel tracker in the sidebar.")
        return
    if df_raw.empty:
        st.warning("⚠️ The loaded dataset is empty or could not be parsed.")
        return

    # ── Calculations ──────────────────────────────────────────────────────────
    total_tools    = len(df_raw)
    good_tools     = df_raw[df_raw["Condition"] == "Good"].shape[0]
    rejected_tools = df_raw[df_raw["Condition"] == "Rejected"].shape[0]
    today          = datetime.now()
    overdue_df     = df_raw[df_raw["Inspection Due Date"].notna() & (df_raw["Inspection Due Date"] < today)]
    total_overdue  = len(overdue_df)

    pct_fit      = good_tools     / total_tools * 100 if total_tools > 0 else 0
    pct_rejected = rejected_tools / total_tools * 100 if total_tools > 0 else 0
    pct_overdue  = total_overdue  / total_tools * 100 if total_tools > 0 else 0

    # ── KPI Row (Beautified to match CSFA) ────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        render_html(kpi_card("Total Registered", "🛠️", f"{total_tools:,}", "#0033a0", "#eef2ff", "#bfdbfe", note="All contractor equipment"))
    with k2:
        render_html(kpi_card("Fit for Use", "✅", f"{good_tools:,}", "#16a34a", "#ecfdf5", "#a7f3d0", note=f"{pct_fit:.0f}% of total inventory"))
    with k3:
        render_html(kpi_card("Defective / Rejected", "❌", f"{rejected_tools:,}", "#dc2626", "#fff5f5", "#fca5a5", note=f"{pct_rejected:.0f}% — replace or repair"))
    with k4:
        render_html(kpi_card("Overdue Inspections", "⏰", f"{total_overdue:,}", "#ea580c", "#fff7ed", "#ffedd5", note=f"{pct_overdue:.0f}% expired certs"))

    # ── Sidebar Filters ───────────────────────────────────────────────────────
    st.sidebar.markdown("<hr style='border-color:rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
    st.sidebar.markdown("<h4 style='color:white;'>🔍 FILTERS</h4>", unsafe_allow_html=True)

    search_query         = st.sidebar.text_input("Search Tool Name / ID", "")
    all_contractors      = sorted(df_raw["Contractor Name"].dropna().unique())
    selected_contractors = st.sidebar.multiselect("Contractors", all_contractors, default=[])
    all_categories       = sorted(df_raw["Category"].dropna().unique())
    selected_categories  = st.sidebar.multiselect("Tool Categories", all_categories, default=[])
    selected_status      = st.sidebar.multiselect("Condition Status", ["Good", "Rejected"], default=[])

    df_filtered = df_raw.copy()
    if search_query:
        df_filtered = df_filtered[
            df_filtered["Tool Name"].astype(str).str.lower().str.contains(search_query.lower())
            | df_filtered["Tool ID"].astype(str).str.lower().str.contains(search_query.lower())
        ]
    if selected_contractors:
        df_filtered = df_filtered[df_filtered["Contractor Name"].isin(selected_contractors)]
    if selected_categories:
        df_filtered = df_filtered[df_filtered["Category"].isin(selected_categories)]
    if selected_status:
        df_filtered = df_filtered[df_filtered["Condition"].isin(selected_status)]

    st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)

    # ── Charts Row 1 ──────────────────────────────────────────────────────────
    c1, c2 = st.columns([1.2, 1])

    with c1:
        with st.container(border=True):
            st.markdown("<h4 style='margin:0; padding-bottom:8px; border-bottom:2px solid #0033a0; color:#002060; font-weight:900; font-size:14px; text-transform:uppercase;'>📊 Equipment Distribution by Category</h4>", unsafe_allow_html=True)
            cat_counts = (
                df_filtered["Category"].value_counts().reset_index()
                .rename(columns={"index": "Category", "Category": "Count"})
            )
            cat_counts.columns = ["Category", "Count"]
            cat_counts = cat_counts.sort_values("Count", ascending=True)

            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
            if not cat_counts.empty:
                PALETTE = [
                    "#0033a0", "#0055b8", "#0ea5e9", "#0f766e",
                    "#059669", "#22c55e", "#d97706", "#ea580c",
                    "#dc2626"
                ]
                colors = PALETTE[: len(cat_counts)]
                fig_cat = go.Figure(go.Bar(
                    y=cat_counts["Category"], x=cat_counts["Count"],
                    orientation="h",
                    marker_color=colors,
                    text=cat_counts["Count"], textposition="outside",
                    textfont=dict(size=12, color="#0f172a", family="Inter"),
                ))
                fig_cat.update_layout(
                    margin=dict(l=5, r=40, t=5, b=5), height=260,
                    xaxis=dict(showgrid=True, gridcolor="#f1f5f9", showticklabels=False),
                    yaxis=dict(showgrid=False, tickfont=dict(size=12, color="#0f172a")),
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                )
                st.plotly_chart(fig_cat, use_container_width=True, config={"displayModeBar": False})
            else:
                st.info("No matching data.")

    with c2:
        with st.container(border=True):
            st.markdown("<h4 style='margin:0; padding-bottom:8px; border-bottom:2px solid #0033a0; color:#002060; font-weight:900; font-size:14px; text-transform:uppercase;'>🏗️ Condition Compliance by Contractor</h4>", unsafe_allow_html=True)
            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
            if not df_filtered.empty:
                grouped = (
                    df_filtered.groupby(["Contractor Name", "Condition"])
                    .size().unstack(fill_value=0).reset_index()
                )
                for col in ["Good", "Rejected"]:
                    if col not in grouped.columns:
                        grouped[col] = 0
                grouped["Total"] = grouped["Good"] + grouped["Rejected"]
                grouped = grouped.sort_values("Total", ascending=False).head(8)

                fig_cond = go.Figure()
                fig_cond.add_trace(go.Bar(
                    y=grouped["Contractor Name"], x=grouped["Good"],
                    name="Good", orientation="h", marker_color="#22c55e",
                ))
                fig_cond.add_trace(go.Bar(
                    y=grouped["Contractor Name"], x=grouped["Rejected"],
                    name="Rejected", orientation="h", marker_color="#ef4444",
                ))
                fig_cond.update_layout(
                    barmode="stack",
                    margin=dict(l=5, r=10, t=5, b=5), height=260,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color="#0f172a")),
                    xaxis=dict(showgrid=True, gridcolor="#f1f5f9"),
                    yaxis=dict(showgrid=False, tickfont=dict(size=11, color="#0f172a")),
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                )
                st.plotly_chart(fig_cond, use_container_width=True, config={"displayModeBar": False})
            else:
                st.info("No matching data.")

    # ── Data Explorer ─────────────────────────────────────────────────────────
    st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("<h4 style='margin:0; padding-bottom:8px; border-bottom:2px solid #0033a0; color:#002060; font-weight:900; font-size:14px; text-transform:uppercase;'>🔍 Detailed Equipment Explorer</h4>", unsafe_allow_html=True)
        st.markdown(f"<div style='font-size:13px; color:#0f172a; font-weight:700; margin-top:10px;'>Showing <b>{len(df_filtered)}</b> of <b>{total_tools}</b> total items.</div>", unsafe_allow_html=True)

        df_display = df_filtered.copy()
        if not df_display.empty:
            for date_col in ["Inspection Date", "Inspection Due Date"]:
                if date_col in df_display.columns:
                    df_display[date_col] = df_display[date_col].apply(
                        lambda x: x.strftime("%d-%b-%Y") if pd.notna(x) else ""
                    )
            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
            st.dataframe(df_display, hide_index=True, use_container_width=True, height=280)

            csv = df_filtered.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Export Filtered Equipment to CSV",
                data=csv,
                file_name="Contractor_Equipment_Report.csv",
                mime="text/csv",
                use_container_width=True,
            )
        else:
            st.info("No matching records found. Modify your filters in the sidebar.")
