# AWS Dashboard Integration & Setup Guide

This guide explains how to connect the Danone Safety Dashboards Streamlit application to AWS S3 (Simple Storage Service, a cloud-based storage service for storing files and datasets) to sync the latest Excel datasets.

---

## 1. AWS Credentials Configuration

To enable S3 integration, the dashboard requires AWS credentials (configured via AWS IAM (Identity and Access Management, a service that helps manage permissions and access control for AWS resources securely)) with read permissions (`s3:GetObject` (the S3 permission action that allows downloading files from a bucket) and `s3:ListBucket` (the S3 permission action that allows listing the contents of a bucket)) on the target bucket.

### Streamlit Secrets Configuration (Recommended)
For secure local execution and cloud deployment, Streamlit provides a built-in secrets manager. Create or edit the file `.streamlit/secrets.toml` in your project root:

```toml
AWS_ACCESS_KEY = "AKIAXXXXXXXXXXXXXXXX"
AWS_SECRET_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
AWS_BUCKET_NAME = "danone-safety-dashboards-bucket"
S3_BASE_FOLDER = "safety_dashboards"
```

> [!WARNING]
> Never commit `.streamlit/secrets.toml` to git. The `.gitignore` file should always contain `.streamlit/secrets.toml` to protect your credentials.

### Environment Variables Fallback
Alternatively, the application can read configuration from your environment variables:
- `AWS_ACCESS_KEY`
- `AWS_SECRET_KEY`
- `AWS_BUCKET_NAME`
- `S3_BASE_FOLDER` (Defaults to `safety_dashboards`)

---

## 2. Bucket Setup and Expected S3 Folder Structure

The dashboard expects Excel files to be uploaded with clean folder namespaces representing their feature areas under the `S3_BASE_FOLDER` prefix.

Ensure your bucket hierarchy matches the following naming exactly:

```text
s3://[your-bucket-name]/[S3_BASE_FOLDER]/
│
├── CSFA/
│   └── CSFA Accumilative data.xlsx
│
├── PTW/
│   └── PTW 1.xlsx
│
├── Tools and Tackles/
│   └── Master - tracker (contractor equipment) update 2026.xlsx
│
└── Workplan/
    └── Himalaya Work Plan - Contractor Wise.xlsx
```

*(Note: The client-side Windows ingestion script `aws_sync_upload.py` automatically maintains this folder structure during uploads.)*

---

## 3. Dashboard Sync Workflow

When running the dashboard:
1. Select a dashboard from the sidebar menu (e.g. **PTW Dashboard**).
2. Look at the **📂 DATA SOURCE** control section in the sidebar.
3. Click the **☁️ Sync AWS** button. This will:
   - Establish a connection to AWS S3.
   - Download the relevant dataset files for the active dashboard page.
   - Cache downloaded files inside the `data/s3_cache/` directory.
   - Write the current timestamp to `data/s3_cache/sync_metadata.json`.
   - Update the UI mode display showing the **Last Synced Timestamp**.
   - Render the visuals dynamically using the newly downloaded S3 cache files.
4. If you wish to go back to local files or manual upload, select use the **📤 Upload Excel** drag-and-drop area.

---

## 4. Troubleshooting & FAQs

### Problem: Dashboard displays "Access Denied (403)" when syncing
- **Reason**: The AWS IAM credentials do not have the required permissions or the bucket name is misspelled.
- **Fix**: Verify your `AWS_BUCKET_NAME`, check that your IAM user/role has an S3 policy allowing `s3:GetObject` and `s3:ListBucket` on `arn:aws:s3:::your-bucket-name` and `arn:aws:s3:::your-bucket-name/*`.

### Problem: Dashboard says "S3 connection successful" but file download fails
- **Reason**: The S3 keys do not match.
- **Fix**: Ensure that the files are in the correct subfolders inside S3. E.g., make sure `PTW 1.xlsx` is under `safety_dashboards/PTW/PTW 1.xlsx`.

### Problem: How do I deploy the app to Streamlit Community Cloud?
1. Deploy your git repository to Streamlit Cloud.
2. In the Streamlit Cloud Dashboard, go to **Settings** -> **Secrets**.
3. Paste the contents of your `secrets.toml` file directly into the text box and click **Save**.
