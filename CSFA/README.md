# Contractor Safety Field Audits Dashboard & Pipeline

This repository contains the safety field audits dashboard and synchronization pipeline built for the safety automation project. It bridges the gap between raw Google/Microsoft Form data (`DRCSFA.xlsx`) and the cleaned analysis dataset (`CSFA Accumilative data.xlsx`) that supports the live dashboard metrics.

## Project Structure

- **[app.py](file:///d:/IITK%20pdfs/Acads/Intern%20stuff/Danone/Pojects%20Projects/Safety%20automation/Dashboards/app.py)**: The main Streamlit application containing the dashboard calculations, Plotly charts, and the data synchronization logic.
- **[trend_classifier_ml.py](file:///d:/IITK%20pdfs/Acads/Intern%20stuff/Danone/Pojects%20Projects/Safety%20automation/Dashboards/trend_classifier_ml.py)**: Placeholder module for predicting observation trends. Uses rule-based or empty-string fallbacks when a trained model is missing, and integrates with the sync pipeline to auto-classify categories when a model is trained.
- **[ml_instructions.md](file:///d:/IITK%20pdfs/Acads/Intern%20stuff/Danone/Pojects%20Projects/Safety%20automation/Dashboards/ml_instructions.md)**: Guide on how to load historical Excel observations, train a classification model on Google Colab, save the trained model as `trend_model.pkl`, and drop it in this folder.
- **[sync_metadata.json](file:///d:/IITK%20pdfs/Acads/Intern%20stuff/Danone/Pojects%20Projects/Safety%20automation/Dashboards/sync_metadata.json)**: Tracks the last synchronized row ID from `DRCSFA.xlsx` to prevent duplicates.
- **[CSFA Accumilative data.xlsx](file:///d:/IITK%20pdfs/Acads/Intern%20stuff/Danone/Pojects%20Projects/Safety%20automation/Dashboards/CSFA%20Accumilative%20data.xlsx)**: The historical cleaned dataset containing manually classified trends and other observation dimensions.
- **[DRCSFA.xlsx](file:///d:/IITK%20pdfs/Acads/Intern%20stuff/Danone/Pojects%20Projects/Safety%20automation/Dashboards/DRCSFA.xlsx)**: The raw sheet containing form responses containing multiple contractor observations per row.

---

## How It Works (The Pipeline)

1. **New Observations Added**: Audits are submitted through the forms, appending raw responses to `DRCSFA.xlsx`.
2. **Synchronization**: Inside the Streamlit dashboard, the user clicks **🔄 Sync DRCSFA Form Data** (or it runs behind the scenes).
   - The sync checks if `DRCSFA.xlsx` contains any rows with `ID` > the ID stored in `sync_metadata.json`.
   - New rows are expanded (since there are up to 10 observations per row) and cleaned.
   - Cleansed observations are appended to `CSFA Accumilative data.xlsx` starting at the first row with an empty description.
   - A sequential serial number is assigned, the status is set to `Pending`, and the `Trend` is set using the ML model if `trend_model.pkl` is available, otherwise left blank.
   - The metadata file is updated with the new maximum processed ID.
3. **Manual Trend Classification**: 
   - Since ML classification is currently skipped, newly added rows will have a blank `Trend` column.
   - The dashboard includes a **Data Quality Helper Table** at the bottom showing any rows missing a `Trend` classification.
   - The team opens the `CSFA Accumilative data.xlsx` Excel file, looks at these rows, and types the appropriate category (e.g. `PPE`, `Housekeeping`, `Work at Height`, etc.) in Column B.
4. **Live Dashboard Rendering**: The dashboard reads directly from the cleaned `CSFA Accumilative data.xlsx` sheet and recalculates all metrics and charts in real-time, matching the categories, averages, and ratio gauges from `severity_dashboard.png`.

---

## Metrics Sourced and Calculated

All metrics are calculated dynamically over the selected date range:
- **Total No. of Contractors**: Count of unique active companies, filtering out note rows.
- **Average Manpower / Day**: Adjustable dynamic sidebar input (defaults to 168).
- **Site Severity Score**: Average severity score of the observations in the date range.
- **Total High Severity Observations**: Count of observations with severity 4 or 5.
- **Observations / Day**: Total high severity observations / count of unique audit dates.
- **Closure Rate**: Percentage of high severity observations marked as `Closed` (case-insensitive).
- **Unsafe Act / Condition Ratio**: Sum of `unsafe acts` / sum of `unsafe Condes`.

---

## Future ML Model Integration

When you are ready to train the ML model for automatic trend classification:
1. Open the [ml_instructions.md](file:///d:/IITK%20pdfs/Acads/Intern%20stuff/Danone/Pojects%20Projects/Safety%20automation/Dashboards/ml_instructions.md) file and follow the Google Colab training guide.
2. Download the resulting `trend_model.pkl` file.
3. Save `trend_model.pkl` in this directory.
4. The dashboard's sync function will automatically detect the file and use it to predict the category for all future synchronized observations.

---

## Running the Dashboard Locally

Make sure the required dependencies are installed:
```bash
pip install streamlit openpyxl pandas plotly
```

Run the Streamlit application:
```bash
streamlit run app.py
```
The application will open in your browser, typically at `http://localhost:8501`.
