import os
import sys
import json
import logging
import time
from typing import List, Dict, Any

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
except ImportError:
    print("Error: 'boto3' package is not installed.")
    print("Please install requirements using: pip install boto3")
    sys.exit(1)

# Configure logging
LOG_FILE = "aws_sync.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("AWSSyncUpload")

CONFIG_FILE = "aws_sync_config.json"

DEFAULT_CONFIG_TEMPLATE = {
    "AWS_ACCESS_KEY": "YOUR_AWS_ACCESS_KEY",
    "AWS_SECRET_KEY": "YOUR_AWS_SECRET_KEY",
    "AWS_BUCKET_NAME": "YOUR_AWS_BUCKET_NAME",
    "S3_BASE_FOLDER": "safety_dashboards",
    "FILE_PATHS": [
        r"C:\path\to\CSFA Accumilative data.xlsx",
        r"C:\path\to\PTW.xlsx",
        r"C:\path\to\PTW Audit.xlsx",
        r"C:\path\to\Master - tracker (contractor equipment) update 2026.xlsx",
        r"C:\path\to\Himalaya Work Plan - Contractor Wise.xlsx"
    ],
    "FOLDER_PATHS": [
        r"C:\path\to\CSFA",
        r"C:\path\to\PTW"
    ],
    "UPLOAD_TIMEOUT_SECONDS": 30
}

def load_or_create_config() -> Dict[str, Any]:
    """Loads config file, or creates a template config file if it does not exist."""
    if not os.path.exists(CONFIG_FILE):
        logger.warning(f"Configuration file '{CONFIG_FILE}' not found. Creating a template configuration file...")
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(DEFAULT_CONFIG_TEMPLATE, f, indent=4)
            logger.info(f"Template config file created at '{CONFIG_FILE}'. Please configure your credentials and run the script again.")
            print(f"\n[ACTION REQUIRED] Configuration template created at '{os.path.abspath(CONFIG_FILE)}'.")
            print("Please edit this file to insert your AWS credentials and file paths before running again.")
            sys.exit(0)
        except Exception as e:
            logger.error(f"Failed to create configuration template: {e}")
            sys.exit(1)
            
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
        return config
    except Exception as e:
        logger.error(f"Failed to parse config file '{CONFIG_FILE}': {e}")
        sys.exit(1)

def upload_file_to_s3(s3_client: Any, local_path: str, bucket_name: str, s3_key: str) -> bool:
    """Uploads a single file to S3 with error logging and performance checks."""
    try:
        logger.info(f"Uploading '{local_path}' to 's3://{bucket_name}/{s3_key}'...")
        start_time = time.time()
        s3_client.upload_file(local_path, bucket_name, s3_key)
        duration = time.time() - start_time
        logger.info(f"Successfully uploaded in {duration:.2f}s")
        return True
    except FileNotFoundError:
        logger.error(f"Local file not found: '{local_path}'")
        return False
    except NoCredentialsError:
        logger.error("AWS credentials not found or invalid.")
        return False
    except ClientError as e:
        logger.error(f"S3 Client Error uploading '{local_path}': {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error uploading '{local_path}': {e}")
        return False

def get_s3_key(local_path: str, s3_base_folder: str) -> str:
    """Generates a clean S3 key keeping the parent folder structure."""
    parent_dir = os.path.basename(os.path.dirname(local_path))
    file_name = os.path.basename(local_path)
    
    # If the parent folder name is not meaningful (e.g. drive letter or root), default to empty
    if len(parent_dir) <= 2 or ":" in parent_dir or parent_dir.lower() in ["dashboards", "desktop", "documents"]:
        parent_dir = ""
        
    s3_key_parts = [s3_base_folder]
    if parent_dir:
        s3_key_parts.append(parent_dir)
    s3_key_parts.append(file_name)
    
    # Standardize forward slashes for S3 keys
    return "/".join([p for p in s3_key_parts if p])

def main():
    logger.info("Starting AWS Sync Upload script...")
    config = load_or_create_config()
    
    # Retrieve configuration values
    access_key = config.get("AWS_ACCESS_KEY", "").strip()
    secret_key = config.get("AWS_SECRET_KEY", "").strip()
    bucket_name = config.get("AWS_BUCKET_NAME", "").strip()
    s3_base_folder = config.get("S3_BASE_FOLDER", "safety_dashboards").strip()
    file_paths = config.get("FILE_PATHS", [])
    folder_paths = config.get("FOLDER_PATHS", [])
    timeout = config.get("UPLOAD_TIMEOUT_SECONDS", 30)
    
    # Validate core credentials
    if access_key == "YOUR_AWS_ACCESS_KEY" or secret_key == "YOUR_AWS_SECRET_KEY" or bucket_name == "YOUR_AWS_BUCKET_NAME":
        logger.error("Please configure real AWS credentials in 'aws_sync_config.json' before running.")
        sys.exit(1)
        
    # Initialize boto3 S3 client
    try:
        session = boto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )
        s3_client = session.client('s3', config=boto3.session.Config(connect_timeout=5, read_timeout=timeout))
    except Exception as e:
        logger.error(f"Failed to initialize S3 Client: {e}")
        sys.exit(1)
        
    success_count = 0
    failure_count = 0
    skipped_count = 0
    
    uploaded_files: List[str] = []
    failed_files: List[str] = []
    
    # Process single file paths
    logger.info(f"Processing {len(file_paths)} individual file paths...")
    for fp in file_paths:
        if not fp:
            continue
        if not os.path.exists(fp):
            logger.warning(f"File path does not exist, skipping: '{fp}'")
            skipped_count += 1
            continue
            
        s3_key = get_s3_key(fp, s3_base_folder)
        success = upload_file_to_s3(s3_client, fp, bucket_name, s3_key)
        if success:
            success_count += 1
            uploaded_files.append(fp)
        else:
            failure_count += 1
            failed_files.append(fp)
            
    # Process folder paths (recursive scan)
    logger.info(f"Processing {len(folder_paths)} folder paths for recursive upload...")
    for folder in folder_paths:
        if not folder:
            continue
        if not os.path.exists(folder):
            logger.warning(f"Folder path does not exist, skipping: '{folder}'")
            skipped_count += 1
            continue
            
        logger.info(f"Scanning folder: '{folder}'")
        for root, _, files in os.walk(folder):
            for file in files:
                # Skip temp/lock Excel files
                if file.startswith("~$") or file.startswith("."):
                    continue
                    
                full_path = os.path.join(root, file)
                # Compute S3 key relative to the folder base
                rel_path = os.path.relpath(full_path, os.path.dirname(folder))
                s3_key = f"{s3_base_folder}/{rel_path.replace(os.sep, '/')}"
                
                success = upload_file_to_s3(s3_client, full_path, bucket_name, s3_key)
                if success:
                    success_count += 1
                    uploaded_files.append(full_path)
                else:
                    failure_count += 1
                    failed_files.append(full_path)
                    
    # Log Upload Summary
    logger.info("=" * 60)
    logger.info("AWS SYNC UPLOAD COMPLETE SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total Successful Uploads : {success_count}")
    logger.info(f"Total Failed Uploads     : {failure_count}")
    logger.info(f"Total Skipped Paths      : {skipped_count}")
    
    if uploaded_files:
        logger.info("\nSuccessful Uploads details:")
        for idx, f in enumerate(uploaded_files, 1):
            logger.info(f"  {idx}. {f}")
            
    if failed_files:
        logger.info("\nFailed Uploads details:")
        for idx, f in enumerate(failed_files, 1):
            logger.warning(f"  {idx}. {f}")
            
    logger.info("=" * 60)
    logger.info("Exiting script.")
    
    # Exit with code 0 if all attempts succeeded, else 1 if failures occurred
    if failure_count > 0:
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()
