import os
import json

# Resolve absolute paths based on this file's location
CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CONFIG_DIR)

CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

# Defaults for Local Paths
DEFAULT_CSFA_PATH = os.path.join(BASE_DIR, "CSFA", "CSFA Accumilative data.xlsx")
DEFAULT_PTW_PATH = os.path.join(BASE_DIR, "PTW", "PTW.xlsx")
DEFAULT_PTW_AUDIT_PATH = os.path.join(BASE_DIR, "PTW", "PTW Audit.xlsx")
DEFAULT_WORKPLAN_PATH = os.path.join(BASE_DIR, "Workplan", "Himalaya Work Plan - Contractor Wise.xlsx")
DEFAULT_TOOLS_PATH = os.path.join(BASE_DIR, "Tools and Tackles", "Master - tracker (contractor equipment) update 2026.xlsx")

# Cache Directories for S3 Downloads
S3_CACHE_DIR = os.path.join(BASE_DIR, "data", "s3_cache")
os.makedirs(S3_CACHE_DIR, exist_ok=True)

# Relative S3 File Keys (matching S3 folder structure)
S3_KEYS = {
    "csfa": "CSFA/CSFA Accumilative data.xlsx",
    "ptw": "PTW/PTW.xlsx",
    "ptw_audit": "PTW/PTW Audit.xlsx",
    "workplan": "Workplan/Himalaya Work Plan - Contractor Wise.xlsx",
    "tools": "Tools and Tackles/Master - tracker (contractor equipment) update 2026.xlsx"
}

def load_config() -> dict:
    """Loads configuration values from config.json if it exists."""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_config(config_data: dict) -> None:
    """Saves updated configurations back to config.json."""
    try:
        with open(CONFIG_PATH, "w") as f:
            json.dump(config_data, f, indent=4)
    except Exception as e:
        print(f"Error saving config.json: {e}")

def get_resolved_path(key: str, default_path: str) -> str:
    """Returns the user-saved path from config.json or falls back to default."""
    config = load_config()
    return config.get(key, default_path)
