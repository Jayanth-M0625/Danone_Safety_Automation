import os
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from io import BytesIO
from typing import Tuple, Dict, Any, Union, Optional

logger = logging.getLogger("DataLoaders")

# ----------------- GENERAL HELPERS -----------------

def clean_dataframe_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Strips whitespace and non-breaking spaces from column names."""
    df.columns = df.columns.astype(str).str.strip().str.replace('\xa0', ' ')
    return df

def normalize_yes_no(val: Any) -> str:
    """Normalizes string inputs to Yes, No, or Unknown."""
    if pd.isna(val):
        return "No"
    s = str(val).strip().lower()
    if s in ["yes", "yes ", "yes  ", "y", "yes", "true", "1", "1.0", "ok"]:
        return "Yes"
    if s in ["no", "n", "false", "0", "0.0", "xx", "none"]:
        return "No"
    # If it is a name or other string that starts with yes/no
    if s.startswith("yes") or s.startswith("y"):
        return "Yes"
    return "No"  # default fallback

# ----------------- CSFA LOADER -----------------

def load_csfa_data(source: Union[str, BytesIO]) -> pd.DataFrame:
    """Loads and processes CSFA dashboard accumilative Excel data."""
    try:
        df = pd.read_excel(source, sheet_name="CSFA Accumilative data")
        df = clean_dataframe_columns(df)
        
        # Filter observations
        obs_col = [c for c in df.columns if "observation discription" in c.lower() or "observation description" in c.lower()]
        if obs_col:
            df = df[df[obs_col[0]].notna()]
        else:
            df = df[df.iloc[:, 2].notna()]
        
        # Parse Dates
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        else:
            df['Date'] = pd.to_datetime(df.iloc[:, 18], errors='coerce') # column 18 is typically Date
            
        # Parse numeric columns
        for num_col in ['Severity', 'Severity ', 'unsafe acts', 'unsafe Condes']:
            if num_col in df.columns:
                clean_name = num_col.strip()
                df[clean_name] = pd.to_numeric(df[num_col], errors='coerce').fillna(0).astype(int)
        
        # Standardize strings
        if 'Status' in df.columns:
            df['Status'] = df['Status'].astype(str).str.strip()
        if 'Contractor name' in df.columns:
            df['Contractor name'] = df['Contractor name'].astype(str).str.strip()
        if 'Trend' in df.columns:
            df['Trend'] = df['Trend'].astype(str).str.strip()
        if 'Zone' in df.columns:
            df['Zone'] = df['Zone'].astype(str).str.strip()
            
        return df
    except Exception as e:
        logger.error(f"Error parsing CSFA Excel: {e}")
        return pd.DataFrame()

# ----------------- PTW LOADER -----------------

def load_ptw_data(ptw_source: Union[str, BytesIO], audit_source: Union[str, BytesIO]) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Loads and processes PTW and PTW Audit Excel data."""
    df_ptw = pd.DataFrame()
    df_audit = pd.DataFrame()
    
    try:
        if isinstance(ptw_source, (str, BytesIO)) or hasattr(ptw_source, 'read'):
            try:
                xl = pd.ExcelFile(ptw_source)
                sheet_name = "PTW" if "PTW" in xl.sheet_names else xl.sheet_names[0]
                df_ptw = xl.parse(sheet_name)
            except Exception:
                df_ptw = pd.read_excel(ptw_source)
        else:
            df_ptw = pd.read_excel(ptw_source)
            
        df_ptw = clean_dataframe_columns(df_ptw)
        if 'PTW Date' in df_ptw.columns:
            df_ptw['PTW Date'] = pd.to_datetime(df_ptw['PTW Date'], errors='coerce')
        if 'Contractor Name' in df_ptw.columns:
            df_ptw['Contractor Name'] = df_ptw['Contractor Name'].astype(str).str.strip()
        else:
            # Check for non-breaking space variation
            for col in df_ptw.columns:
                if "contractor" in col.lower():
                    df_ptw['Contractor Name'] = df_ptw[col].astype(str).str.strip()
                    break
    except Exception as e:
        logger.error(f"Error parsing PTW Excel: {e}")
        
    try:
        if isinstance(audit_source, (str, BytesIO)) or hasattr(audit_source, 'read'):
            try:
                xl = pd.ExcelFile(audit_source)
                sheet_name = "PTW Audit" if "PTW Audit" in xl.sheet_names else xl.sheet_names[0]
                df_audit = xl.parse(sheet_name)
            except Exception:
                df_audit = pd.read_excel(audit_source)
        else:
            df_audit = pd.read_excel(audit_source)
            
        df_audit = clean_dataframe_columns(df_audit)
        if 'Date' in df_audit.columns:
            df_audit['Date'] = pd.to_datetime(df_audit['Date'], errors='coerce')
        if 'Contractor' in df_audit.columns:
            df_audit['Contractor'] = df_audit['Contractor'].astype(str).str.strip()
    except Exception as e:
        logger.error(f"Error parsing PTW Audit Excel: {e}")
        
    return df_ptw, df_audit

# ----------------- TOOLS & TACKLES LOADER -----------------

def normalize_tool_status(status: Any) -> str:
    """Standardizes equipment condition to Good or Rejected."""
    if pd.isna(status):
        return "Good" # Assume good if blank
    s = str(status).strip().lower()
    if "not" in s or "reject" in s or "fail" in s or "bad" in s or "no" in s:
        return "Rejected"
    return "Good"

def load_tools_data(source: Union[str, BytesIO]) -> pd.DataFrame:
    """Loads and standardizes Tools & Tackles Excel sheets into a single master DataFrame."""
    all_tools = []
    
    try:
        xl = pd.ExcelFile(source)
        for sheet in xl.sheet_names:
            df_raw = xl.parse(sheet)
            if len(df_raw) < 2:
                continue
                
            # Second row (index 1) contains the actual column headers
            headers = df_raw.iloc[1].tolist()
            headers = [str(h).strip().replace('\n', ' ') for h in headers]
            
            df_data = df_raw.iloc[2:].copy()
            df_data.columns = headers
            df_data = clean_dataframe_columns(df_data)
            
            # Find matching column indices for standardized schema
            tool_name_col = None
            tool_id_col = None
            status_col = None
            insp_date_col = None
            due_date_col = None
            contractor_col = None
            remarks_col = None
            
            for col in df_data.columns:
                col_lower = col.lower()
                if "tool" in col_lower and "name" in col_lower:
                    tool_name_col = col
                elif "description" in col_lower or "item" in col_lower or "name" in col_lower:
                    if not tool_name_col:
                        tool_name_col = col
                if "id" in col_lower or "code" in col_lower or "quantity" in col_lower:
                    tool_id_col = col
                if "condition" in col_lower or "status" in col_lower:
                    status_col = col
                if "inspection date" in col_lower or "last inspection" in col_lower:
                    insp_date_col = col
                if "due" in col_lower:
                    due_date_col = col
                if "contractor" in col_lower:
                    contractor_col = col
                if "remark" in col_lower:
                    remarks_col = col
            
            # Extract and standardize rows
            for _, r in df_data.iterrows():
                # Skip rows that are completely empty
                if r.isna().all() or pd.isna(r.iloc[0]) and pd.isna(r.iloc[1]):
                    continue
                    
                tool_name = str(r[tool_name_col]).strip() if tool_name_col and pd.notna(r[tool_name_col]) else "Unknown Equipment"
                tool_id = str(r[tool_id_col]).strip() if tool_id_col and pd.notna(r[tool_id_col]) else "N/A"
                
                # Skip title header row duplicates or empty rows
                if "tools name" in tool_name.lower() or "item description" in tool_name.lower():
                    continue
                    
                raw_status = r[status_col] if status_col and pd.notna(r[status_col]) else "Good"
                status = normalize_tool_status(raw_status)
                
                insp_date = pd.to_datetime(r[insp_date_col], errors='coerce') if insp_date_col else pd.NaT
                due_date = pd.to_datetime(r[due_date_col], errors='coerce') if due_date_col else pd.NaT
                
                contractor = str(r[contractor_col]).strip() if contractor_col and pd.notna(r[contractor_col]) else "Unknown Contractor"
                remarks = str(r[remarks_col]).strip() if remarks_col and pd.notna(r[remarks_col]) else ""
                
                all_tools.append({
                    "Category": sheet.strip(),
                    "Tool Name": tool_name,
                    "Tool ID": tool_id,
                    "Condition": status,
                    "Inspection Date": insp_date,
                    "Inspection Due Date": due_date,
                    "Contractor Name": contractor,
                    "Remarks": remarks
                })
                
        if not all_tools:
            return pd.DataFrame()
            
        master_df = pd.DataFrame(all_tools)
        # Type conversions
        master_df["Inspection Date"] = pd.to_datetime(master_df["Inspection Date"])
        master_df["Inspection Due Date"] = pd.to_datetime(master_df["Inspection Due Date"])
        return master_df
    except Exception as e:
        logger.error(f"Error parsing Tools & Tackles Excel: {e}")
        return pd.DataFrame()

# ----------------- WORKPLAN LOADER -----------------

def load_workplan_data(source: Union[str, BytesIO]) -> pd.DataFrame:
    """Loads and standardizes Workplan Excel sheets into a single master DataFrame."""
    all_activities = []
    
    try:
        xl = pd.ExcelFile(source)
        for sheet in xl.sheet_names:
            if sheet in ["Guidelines", "Sheet1"]:
                continue
                
            df_raw = xl.parse(sheet)
            if len(df_raw) < 2:
                continue
                
            # Row index 0 contains the headers
            headers = df_raw.iloc[0].tolist()
            headers = [str(h).strip().replace('\n', ' ') for h in headers]
            
            df_data = df_raw.iloc[1:].copy()
            df_data.columns = headers
            df_data = clean_dataframe_columns(df_data)
            
            # Map columns
            supplier_col = None
            date_col = None
            desc_col = None
            permit_col = None
            location_col = None
            crit_col = None
            hira_col = None
            ms_col = None
            verified_col = None
            
            for col in df_data.columns:
                col_lower = col.lower()
                if "supplier" in col_lower or "contractor name" in col_lower:
                    supplier_col = col
                elif "date" in col_lower:
                    date_col = col
                elif "description" in col_lower:
                    desc_col = col
                elif "permit" in col_lower or "type of job" in col_lower:
                    permit_col = col
                elif "location" in col_lower or "area" in col_lower:
                    if not location_col or "owner" not in col_lower:
                        location_col = col
                elif "critical activities" in col_lower:
                    crit_col = col
                elif "hira" in col_lower or "jsa" in col_lower:
                    hira_col = col
                elif "method statement" in col_lower:
                    ms_col = col
                elif "verified by area" in col_lower:
                    verified_col = col
            
            for _, r in df_data.iterrows():
                # Skip sample rows or fully empty rows
                supplier_val = str(r[supplier_col]).strip() if supplier_col and pd.notna(r[supplier_col]) else ""
                if "sample" in supplier_val.lower():
                    continue
                if date_col and pd.isna(r[date_col]):
                    continue
                if r.isna().all():
                    continue
                    
                # Standardize values
                contractor = supplier_val if supplier_val else sheet.strip()
                act_date = pd.to_datetime(r[date_col], dayfirst=True, errors='coerce') if date_col else pd.NaT
                work_desc = str(r[desc_col]).strip() if desc_col and pd.notna(r[desc_col]) else ""
                permit_type = str(r[permit_col]).strip() if permit_col and pd.notna(r[permit_col]) else "General"
                area = str(r[location_col]).strip() if location_col and pd.notna(r[location_col]) else "Site"
                crit_act = str(r[crit_col]).strip() if crit_col and pd.notna(r[crit_col]) else ""
                
                hira_status = normalize_yes_no(r[hira_col]) if hira_col else "No"
                ms_status = normalize_yes_no(r[ms_col]) if ms_col else "No"
                verified_status = normalize_yes_no(r[verified_col]) if verified_col else "No"
                
                all_activities.append({
                    "Contractor Name": contractor,
                    "Date": act_date,
                    "Work Description": work_desc,
                    "Permit Type": permit_type,
                    "Area": area,
                    "Critical Activities": crit_act,
                    "HIRA/JSA Status": hira_status,
                    "Method Statement Status": ms_status,
                    "Verified": verified_status
                })
                
        if not all_activities:
            return pd.DataFrame()
            
        master_df = pd.DataFrame(all_activities)
        master_df["Date"] = pd.to_datetime(master_df["Date"])
        return master_df
    except Exception as e:
        logger.error(f"Error parsing Workplan Excel: {e}")
        return pd.DataFrame()
