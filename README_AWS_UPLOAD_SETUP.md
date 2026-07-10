# AWS S3 Ingestion Tool - Setup and Configuration Guide

This guide covers setting up and running the standalone Python utility `aws_sync_upload.py` to upload safety dashboards Excel files from a local Windows laptop to AWS S3.

---

## 1. Prerequisites & Installation

### Step A: Install Python on Windows
1. Download the latest Python 3.11+ installer from [python.org](https://www.python.org/downloads/).
2. Run the installer and **Check the box** that says **"Add Python.exe to PATH"** (Critical for running python from the Command Prompt).
3. Select **Install Now** and follow the instructions.

### Step B: Install Package Requirements
Open your Command Prompt (`cmd`) and install the AWS SDK for Python (`boto3`):
```bash
pip install boto3
```

---

## 2. Configuring the Sync Utility

1. Run the script once to generate the default configuration template:
   ```bash
   python aws_sync_upload.py
   ```
   This will create a file named `aws_sync_config.json` in the same directory and exit.

2. Open `aws_sync_config.json` in any text editor (e.g., Notepad) and configure your credentials and target file paths:

```json
{
    "AWS_ACCESS_KEY": "AKIAXXXXXXXXXXXXXXXX",
    "AWS_SECRET_KEY": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    "AWS_BUCKET_NAME": "danone-safety-dashboards-bucket",
    "S3_BASE_FOLDER": "safety_dashboards",
    "FILE_PATHS": [
        "D:\\IITK pdfs\\Acads\\Intern stuff\\Danone\\Pojects Projects\\Safety automation\\Dashboards\\CSFA\\CSFA Accumilative data.xlsx",
        "D:\\IITK pdfs\\Acads\\Intern stuff\\Danone\\Pojects Projects\\Safety automation\\Dashboards\\PTW\\PTW.xlsx",
        "D:\\IITK pdfs\\Acads\\Intern stuff\\Danone\\Pojects Projects\\Safety automation\\Dashboards\\PTW\\PTW Audit.xlsx",
        "D:\\IITK pdfs\\Acads\\Intern stuff\\Danone\\Pojects Projects\\Safety automation\\Dashboards\\Tools and Tackles\\Master - tracker (contractor equipment) update 2026.xlsx",
        "D:\\IITK pdfs\\Acads\\Intern stuff\\Danone\\Pojects Projects\\Safety automation\\Dashboards\\Workplan\\Himalaya Work Plan - Contractor Wise.xlsx"
    ],
    "FOLDER_PATHS": [],
    "UPLOAD_TIMEOUT_SECONDS": 45
}
```

### Configuration Parameters Explained:
- **`AWS_ACCESS_KEY` / `AWS_SECRET_KEY`**: Your AWS IAM credentials with `s3:PutObject` permissions.
- **`AWS_BUCKET_NAME`**: Name of the target S3 bucket.
- **`S3_BASE_FOLDER`**: The top-level folder prefix in your S3 bucket (e.g., `safety_dashboards`).
- **`FILE_PATHS`**: List of direct paths to files you want synced. The folder hierarchy (e.g., `CSFA/`, `PTW/`) will be inferred from parent directories.
- **`FOLDER_PATHS`**: List of directories to recursively scan and upload.
- **`UPLOAD_TIMEOUT_SECONDS`**: Maximium time to wait for a file upload chunk before timeout (default 30s).

---

## 3. Testing Upload Manually

Run the upload script via Command Prompt:
```bash
python aws_sync_upload.py
```

### Verification
1. Review the output in the console. You should see a detailed summary:
   ```text
   ============================================================
   AWS SYNC UPLOAD COMPLETE SUMMARY
   ============================================================
   Total Successful Uploads : 5
   Total Failed Uploads     : 0
   Total Skipped Paths      : 0
   ============================================================
   ```
2. Check the `aws_sync.log` file created in the same folder.
3. Log into your **AWS Management Console**, navigate to the **S3 Bucket**, and verify that the files are present in the folder hierarchy matching the structure:
   - `s3://[YOUR-BUCKET]/safety_dashboards/CSFA/CSFA Accumilative data.xlsx`
   - `s3://[YOUR-BUCKET]/safety_dashboards/PTW/PTW.xlsx`
   - `s3://[YOUR-BUCKET]/safety_dashboards/PTW/PTW Audit.xlsx`
   - `s3://[YOUR-BUCKET]/safety_dashboards/Tools and Tackles/Master - tracker (contractor equipment) update 2026.xlsx`
   - `s3://[YOUR-BUCKET]/safety_dashboards/Workplan/Himalaya Work Plan - Contractor Wise.xlsx`

---

## 4. Automating with Windows Task Scheduler

To ensure real-time dashboards sync continuously, automate the script run using Windows Task Scheduler.

### Step-by-Step Task Creation:

1. Press `Win + R`, type `taskschd.msc`, and press Enter.
2. In the right-hand panel, click **Create Task...** (Do not click *Create Basic Task*).
3. **General Tab**:
   - **Name**: `Danone Safety Dashboards AWS Sync`
   - **Description**: `Uploads local safety Excel data to AWS S3 every 30 minutes.`
   - Under *Security Options*: Select **"Run whether user is logged on or not"**.
   - Check **"Run with highest privileges"** to prevent execution restrictions.
   - Configure for: **Windows 10** or **Windows 11** (depending on your OS).
4. **Triggers Tab**:
   - Click **New...**
   - **Begin the task**: `At startup`.
   - Under *Advanced settings*:
     - Check **Repeat task every**: Select `30 minutes`.
     - Set **for a duration of**: `Indefinitely`.
     - Check **Enabled**.
     - Click **OK**.
5. **Actions Tab**:
   - Click **New...**
   - **Action**: `Start a program`.
   - **Program/script**: Enter the path to your python executable, usually `python.exe` or `C:\Users\[username]\AppData\Local\Programs\Python\Python312\python.exe`.
   - **Add arguments (optional)**: Enter the script filename, `aws_sync_upload.py`.
   - **Start in (optional)**: Enter the folder path where `aws_sync_upload.py` and `aws_sync_config.json` reside, e.g., `D:\IITK pdfs\Acads\Intern stuff\Danone\Pojects Projects\Safety automation\Dashboards`. (Crucial so it resolves configurations and logs correctly!).
   - Click **OK**.
6. **Settings Tab**:
   - Check **"Run task as soon as possible after a scheduled start is missed"**.
   - Check **"If the task fails, restart every"**: Set to `5 minutes`, and attempt to restart up to `3 times`.
   - Click **OK**.
7. When prompted, enter your Windows Account Password to finalize permissions (necessary for tasks configured to run when logged out).
