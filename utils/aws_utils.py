import os
import json
import logging
from datetime import datetime
from typing import Tuple, Dict, Any
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from config.aws_config import AWS_ACCESS_KEY, AWS_SECRET_KEY, AWS_BUCKET_NAME, S3_BASE_FOLDER
from config.dashboard_config import S3_KEYS, S3_CACHE_DIR

logger = logging.getLogger("AWSUtils")

METADATA_PATH = os.path.join(S3_CACHE_DIR, "sync_metadata.json")

def get_s3_client() -> Any:
    """Initializes and returns a boto3 S3 client using configured credentials."""
    if not AWS_ACCESS_KEY or not AWS_SECRET_KEY:
        raise ValueError("AWS Credentials are not configured. Please check Streamlit Secrets or environment variables.")
    
    session = boto3.Session(
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY
    )
    return session.client('s3')

def test_s3_connection() -> Tuple[bool, str]:
    """Tests connection to AWS S3 bucket."""
    try:
        s3 = get_s3_client()
        # Test connection by listing a single object (limit=1) or checking bucket status
        s3.head_bucket(Bucket=AWS_BUCKET_NAME)
        return True, "S3 connection successful."
    except ValueError as ve:
        return False, str(ve)
    except ClientError as ce:
        error_code = ce.response.get('Error', {}).get('Code', 'Unknown')
        if error_code == '403':
            return False, f"Access Denied (403) for bucket '{AWS_BUCKET_NAME}'."
        elif error_code == '404':
            return False, f"Bucket '{AWS_BUCKET_NAME}' not found (404)."
        return False, f"S3 connection failed: {ce}"
    except Exception as e:
        return False, f"Failed to connect to S3: {e}"

def download_s3_file(s3_key_suffix: str, local_filename: str) -> bool:
    """Downloads a file from AWS S3 to the local cache folder."""
    try:
        s3 = get_s3_client()
        s3_key = f"{S3_BASE_FOLDER}/{s3_key_suffix}"
        local_path = os.path.join(S3_CACHE_DIR, local_filename)
        
        logger.info(f"Downloading s3://{AWS_BUCKET_NAME}/{s3_key} to {local_path}...")
        s3.download_file(AWS_BUCKET_NAME, s3_key, local_path)
        return True
    except Exception as e:
        logger.error(f"Failed to download S3 key '{s3_key_suffix}': {e}")
        return False

def sync_all_from_s3() -> Tuple[bool, str]:
    """Syncs all configured files from S3 and updates last sync timestamp."""
    success = True
    downloaded_files = []
    failed_files = []
    
    # Verify S3 connection first
    conn_ok, conn_msg = test_s3_connection()
    if not conn_ok:
        return False, conn_msg

    for db_key, s3_suffix in S3_KEYS.items():
        # Derive local filename: e.g. for key "ptw_audit" it becomes "PTW Audit.xlsx"
        local_filename = os.path.basename(s3_suffix)
        result = download_s3_file(s3_suffix, local_filename)
        if result:
            downloaded_files.append(local_filename)
        else:
            success = False
            failed_files.append(local_filename)
            
    if success:
        # Update metadata timestamp
        update_sync_metadata()
        msg = f"All files synced successfully: {', '.join(downloaded_files)}"
    else:
        msg = f"Sync completed with errors. Downloaded: {', '.join(downloaded_files)}. Failed: {', '.join(failed_files)}."
        
    return success, msg

def get_last_sync_timestamp() -> str:
    """Retrieves the last successful sync timestamp from local cache metadata."""
    if os.path.exists(METADATA_PATH):
        try:
            with open(METADATA_PATH, "r") as f:
                meta = json.load(f)
                return meta.get("last_sync", "Never Synced")
        except Exception:
            return "Never Synced"
    return "Never Synced"

def update_sync_metadata() -> None:
    """Updates the sync timestamp metadata to current local time."""
    now_str = datetime.now().strftime("%d-%b-%Y %I:%M %p")
    try:
        meta = {"last_sync": now_str}
        with open(METADATA_PATH, "w") as f:
            json.dump(meta, f)
    except Exception as e:
        logger.error(f"Failed to update sync metadata: {e}")

def initialize_s3_cache_from_local() -> None:
    """If the S3 cache files do not exist, populate them from the default local directories."""
    import shutil
    from config.dashboard_config import S3_KEYS, S3_CACHE_DIR, BASE_DIR
    
    local_paths = {
        "csfa": os.path.join(BASE_DIR, "CSFA", "CSFA Accumilative data.xlsx"),
        "ptw": os.path.join(BASE_DIR, "PTW", "PTW 1.xlsx"),
        "ptw_audit": os.path.join(BASE_DIR, "PTW", "PTW 1.xlsx"),
        "workplan": os.path.join(BASE_DIR, "Workplan", "Himalaya Work Plan - Contractor Wise.xlsx"),
        "tools": os.path.join(BASE_DIR, "Tools and Tackles", "Master - tracker (contractor equipment) update 2026.xlsx")
    }
    
    any_copied = False
    for key, s3_suffix in S3_KEYS.items():
        local_filename = os.path.basename(s3_suffix)
        cache_path = os.path.join(S3_CACHE_DIR, local_filename)
        
        # If cache file does not exist, copy from local if possible
        if not os.path.exists(cache_path):
            src_path = local_paths.get(key)
            if src_path and os.path.exists(src_path):
                logger.info(f"Populating cache: copying '{src_path}' to '{cache_path}'")
                try:
                    shutil.copy2(src_path, cache_path)
                    any_copied = True
                except Exception as e:
                    logger.error(f"Failed to copy '{src_path}' to cache: {e}")
                    
    if any_copied and get_last_sync_timestamp() == "Never Synced":
        # Update metadata to show it was initialized from local
        now_str = datetime.now().strftime("%d-%b-%Y %I:%M %p")
        try:
            meta = {"last_sync": f"Initialized from Local ({now_str})"}
            with open(METADATA_PATH, "w") as f:
                json.dump(meta, f)
        except Exception as e:
            logger.error(f"Failed to update sync metadata: {e}")
