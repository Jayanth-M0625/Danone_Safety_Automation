# Contractor Safety Field Audits (CSFA) Dashboard

This folder contains the datasets and assets supporting the CSFA (Contractor Safety Field Audits) Dashboard page in the safety dashboards application.

## Directory Contents

- **`CSFA Accumilative data.xlsx`**: The primary Excel dataset containing cleaned and processed safety audit observations, dates, severity scores (ranging 1-5), zones, and unsafe acts/conditions.
- **`danone_logo.png`**: Logo asset used in the dashboard interface.
- **`severity_dashboard.png`**: Reference image showing the expected layout and style of the dashboard UI.
- **`sync_metadata.json`**: An obsolete metadata file from previous implementations (which tracked sync IDs). It is not active in the current data source loader.

---

## How It Works

1. **Data Source Resolution**: The dashboard loads safety field audit data from one of three sources (selected via the sidebar in the dashboard interface):
   - **Local File (Default)**: Resolves to `CSFA Accumilative data.xlsx` in this folder.
   - **AWS S3 Cache**: Clicking **☁️ Sync AWS** downloads the latest `CSFA Accumilative data.xlsx` from AWS S3 (Simple Storage Service, a cloud-based storage service for storing files and datasets) into the cache directory (`data/s3_cache/`) and renders it.
   - **Uploaded Excel**: Users can upload custom `.xlsx` files directly through the **📤 Upload Excel** component to visualize custom data on the fly.
   
2. **Metrics Sourced and Calculated**:
   - **Total No. of Contractors**: Count of unique active companies, excluding standard non-contractor entries (like general, common area, etc.).
   - **Average Manpower / Day**: Dynamic average manpower value specified via a sidebar slider (defaults to 168).
   - **Site Severity Score**: Mean severity score of observations recorded during the filtered date range.
   - **Total High Severity Observations**: Count of records with a severity score of 4 or 5.
   - **Observations / Day**: High severity observations divided by unique audit dates.
   - **Closure Rate**: Percentage of high severity observations marked as `Closed` (case-insensitive).
   - **Unsafe Act / Condition Ratio**: Sum of unsafe acts divided by the sum of unsafe conditions.

3. **Visualizations**:
   - **Top Observation Categories**: Horizontal bar chart showing counts of observation trends/categories (e.g. PPE, Housekeeping).
   - **Audit Distribution by Zone**: Bar chart representing audit counts per site zone.
   - **Monthly Observation Trend**: Line chart illustrating monthly observation counts.
   - **Zone Safety Score**: Matrix view of zone compliance and risk metrics.
   - **Data Quality Helper Table**: Displays rows that are missing key classification labels (like 'Trend') to help data administrators identify records that require manual updates.
