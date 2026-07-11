# Workplan Dashboard – Metric Calculation and Display Guide

This documentation guide details the formulas, classification logic, and visual representations used in the **Workplan Dashboard** (High Risk Activities – Risk Management Overview).

---

## 1. Data Source Schema

The dashboard parses contractor weekly work plan sheets inside `Himalaya Work Plan - Contractor Wise.xlsx` (standardized by `utils/data_loaders.py`). The loader standardizes each sheet into a unified schema:

- **Contractor Name**: Name of the contractor executing the job (derived from the column or sheet name).
- **Date**: Planned execution date.
- **Work Description**: Description of the task.
- **Permit Type**: The type of Permit to Work (e.g. general, hot, height).
- **Area**: Specific location where the task takes place.
- **Critical Activities**: Text list of hazards/critical control steps (separated by newlines).
- **HIRA/JSA Status**: Indicates if a Hazard Identification & Risk Assessment/Job Safety Analysis was completed (Yes/No).
- **Method Statement Status**: Indicates if a Method Statement (a document describing the safe execution sequence) was prepared (Yes/No).
- **Verified**: Indicates if controls were verified on-site by area owners (Yes/No).

---

## 2. Metric Calculations

### 1. Planned Activities
- **Definition**: The total count of scheduled contractor tasks in the active reporting window.
- **Formula**:
  $$Planned = \text{Total row count in dataset } (len(df))$$

### 2. JSA Prepared (Assessed)
- **Definition**: Count of scheduled activities that have completed the Hazard Identification & Risk Assessment/Job Safety Analysis.
- **Formula**:
  $$Assessed = \text{Rows where } [HIRA/JSA\ Status] == "Yes"$$

### 3. Method Statement Prepared
- **Definition**: Count of scheduled activities that have a finalized Method Statement.
- **Formula**:
  $$\text{Method Statements} = \text{Rows where } [Method\ Statement\ Status] == "Yes"$$

### 4. Gap
- **Definition**: The number of planned tasks currently lacking a JSA assessment.
- **Formula**:
  $$Gap = \max(0, Planned - Assessed)$$

### 5. Critical Controls Identified
- **Definition**: The cumulative sum of all hazard controls identified across all scheduled tasks.
- **Formula**:
  - For each row, the text in `Critical Activities` is split by newline (`\n`).
  - Empty lines and entries starting with `"no"` (case-insensitive) are excluded.
  - If the resulting list of controls is empty, a default fallback of `0` controls is assigned to that activity.
  - The final metric is the sum of these controls across all activities.

### 6. Critical Controls Ready for Execution
- **Definition**: The total number of controls deemed fully ready and verified on-site.
- **Formula**:
  - For each activity, if `Verified` is `"Yes"`, **100%** of its identified controls are marked "ready".
  - If `Verified` is `"No"`, **0%** of its controls are marked "ready" (meaning unverified activities contribute nothing to execution readiness).
  - The final metric is the sum of ready controls across all activities.

### 7. Risk in Executions Classification
Every planned task is grouped into a risk profile based on JSA, Method Statement, and Verification status:

| Risk Category | Criteria | Action & Display Status |
|---|---|---|
| **High Risk** | `HIRA/JSA Status` != "Yes" **AND** `Method Statement Status` != "Yes" | Classified as High Risk in Executions |
| **Medium Risk** | `HIRA/JSA Status` != "Yes" **OR** `Method Statement Status` != "Yes" (but not both) | Classified as Medium Risk in Executions |
| **Low Risk** | `HIRA/JSA Status` == "Yes" **AND** `Method Statement Status` == "Yes", but `Verified` != "Yes" | Classified as Low Risk in Executions |
| **Very Low Risk** | `HIRA/JSA Status` == "Yes" **AND** `Method Statement Status` == "Yes" **AND** `Verified` == "Yes" | Classified as Very Low Risk in Executions |

*Note: An activity is flagged as `is_high_risk` if it falls in the High or Medium risk categories.*

---

## 3. Critical Activity Classification (Categories)

Activities are dynamically grouped into one of three critical activity areas by combining `Permit Type`, `Critical Activities`, and `Work Description` fields and searching for keywords:

1. **Heavy Lifting & Shifting**: If combined text contains: `lifting`, `shifting`, `crane`, `farana`, `hopt`, `pulley`, or `hoist`.
2. **Work at Height**: If combined text contains: `height`, `scaffold`, `ladder`, `roof`, `fall`, or `boom lift`.
3. **Civil Works**: Any activity not matching the keywords of the first two groups is classified here by default.

---

## 4. UI Display and Visualizations

The calculated metrics are mapped to dashboard UI components as follows:

### KPI Header Row
- **Planned vs Risk Assessment Donut Chart**: Shows the percentage of tasks assessed ($Assessed / Planned$). A legend details the raw numbers, and a badge at the bottom displays the remaining $Gap$.
- **No. of Critical Controls Identified Card**: Renders the total identified controls.
- **No. of JSA Prepared Card**: Renders total JSAs prepared.
- **No. of Method Statement Prepared Card**: Renders total Method Statements.
- **No. of Critical Controls Ready Card**: Renders the ready count and the percentage of readiness relative to identified controls.
- **Risk in Executions Pie Chart**: Donut chart displaying the proportion of High, Medium, Low, and Very Low risk tasks.

### Reference Data Table
Displays a category-by-category breakdown table (🏗️ Heavy Lifting & Shifting, 🧗 Work at Height, 🧱 Civil Works, and TOTAL) containing:
- **Assessments Completed**: `Completed / Planned` ($Count\ (\%)$).
- **Critical Controls Identified**: Total count of controls.
- **Critical Controls Ready**: Total ready controls and percentage ($Count\ (\%)$).
- **Compliance for Execution**: $Completed / Planned$ percentage.
- **High Risks in Execution**: Total high+medium risk tasks and percentage ($Count\ (\%)$ rendered in bold red).
