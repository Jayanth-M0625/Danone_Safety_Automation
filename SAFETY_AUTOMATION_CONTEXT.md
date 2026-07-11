# Safety Automation Dashboards - Developer & AI Context

This file serves as a handoff and context document for developer engineers and AI coding assistants working on this repository.

---

## 1. Project Overview

This repository is a premium, enterprise-grade safety dashboard suite for **Danone**, built with **Streamlit**, **Pandas**, and **Plotly**. It visualizes safety audits, work permits, equipment inspections, and weekly safety work plans. It is integrated with AWS S3 (Simple Storage Service, a cloud-based storage service for storing files and datasets) for data synchronization.

---

## 2. Directory Layout & Key Files

```text
├── .streamlit/
│   └── secrets.toml          # AWS credentials configuration for cloud/local sync
│
├── config/
│   ├── aws_config.py         # Loads S3 access keys, secret key, bucket settings
│   └── dashboard_config.py   # Resolves local paths, S3 keys, and cache directories
│
├── dashboards/
│   ├── __init__.py           # Reusable sidebar data source selector UI
│   ├── csfa_dashboard.py     # Observation trends, severity gauge, zone score bar charts
│   ├── ptw_dashboard.py      # Audits counts, compliance donuts, violators table
│   ├── tools_tackles_dashboard.py # [NEW] Equipment inspections (power, hand, PPE, harnesses)
│   └── workplan_dashboard.py # [NEW] Dynamic weekly work plan (Planned vs HIRA JSA)
│
├── utils/
│   ├── __init__.py
│   ├── aws_utils.py          # Handles S3 connection test and file downloads
│   └── data_loaders.py       # Core parsing pipelines for Excel -> Standard Pandas DataFrames
│
├── data/
│   └── s3_cache/             # Target folder for AWS S3 cached datasets
│
├── app.py                    # Main app coordinator, styling injector, page router
│   └── run_dashboard.bat     # Windows batch script to launch the local Streamlit dashboard
│
├── aws_sync_upload.py        # Client Windows utility to sync local files to S3
├── config.json               # Shared dynamic settings for OneDrive/SharePoint paths
└── requirements.txt          # Python dependencies
```

---

## 3. Data Source Architecture

Each of the dashboards supports three distinct data sources loaded via the exact same processing pipeline in `utils/data_loaders.py`:

1. **Local Files (Default)**: Path configuration resolved dynamically via `config.json` (OneDrive/SharePoint synced paths) or falling back to default folders in the workspace.
2. **AWS S3 Latest Data**: Triggered by the `[Sync AWS]` sidebar button. Downloads files from S3 into `data/s3_cache/` and caches them locally, rendering with S3 cached copies and writing timestamp metadata.
3. **User Uploaded File**: Handled via `st.file_uploader` in Streamlit. Processes uploaded Excel bytes directly in memory.

---

## 4. Key Schemas and Loaders

All pipelines are in `utils/data_loaders.py`:

- **CSFA**: Parses `CSFA Accumilative data.xlsx` -> Sheet `CSFA Accumilative data`. Clean observations, dates, severity scores (1-5), and unsafe acts/conditions.
- **PTW**: Parses `PTW 1.xlsx` (containing both issued permits and audited permits sheets). Joins them on `PTW No` to calculate compliance (`(total_issued - total_observations)/total_issued * 100`), critical violations, and contractors.
- **Tools & Tackles**: Loops through 9 sheets (`Power tools`, `Hand tools`, `PPE's`, etc.). Standardizes column headers at row index 1. Maps equipment condition to `Good` or `Rejected` and calculates inspection overdue dates.
- **Work Plan**: Standardizes multiple contractor sheets (`GEA`, `SPX Flo`, etc.) by inspecting header formats at row index 0. Extracts HIRA/JSA approvals and Method Statement yes/no, classifying actions into risk profiles.

---

## 5. UI Theme & Styles

The application injects custom premium styles defined in `app.py`:
- **Typography**: Inter (Google Fonts), Danone One.
- **Color Palette**: Deep Danone Blue (`#002256`, `#0033a0`), Emerald Green (`#10b981`), Soft Red (`#fa5252`, `#ef4444`).
- **Cards**: All containers use equal height layouts and `data-testid="stVerticalBlockBorderDiv"` white boxes with standard borders and shadows for premium aesthetic consistency.
