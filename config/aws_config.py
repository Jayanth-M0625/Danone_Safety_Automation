import os
import streamlit as st

def get_aws_secret(key: str, default: str = "") -> str:
    """Helper to load secrets from Streamlit Secrets, environment variables, or local config."""
    # 1. Try Streamlit Secrets
    try:
        if st.secrets and key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    
    # 2. Try Environment Variables
    return os.getenv(key, default)

# AWS Global Configuration Variables
AWS_ACCESS_KEY = get_aws_secret("AWS_ACCESS_KEY")
AWS_SECRET_KEY = get_aws_secret("AWS_SECRET_KEY")
AWS_BUCKET_NAME = get_aws_secret("AWS_BUCKET_NAME")
S3_BASE_FOLDER = get_aws_secret("S3_BASE_FOLDER", "safety_dashboards")
