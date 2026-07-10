import os
import streamlit as st
from utils.aws_utils import get_last_sync_timestamp, sync_all_from_s3, initialize_s3_cache_from_local

def render_source_selector(dashboard_key: str) -> str:
    """Renders the standard data source buttons and file uploader in the sidebar.
    
    Returns the active source: 'aws' or 'upload'.
    """
    # Seed S3 cache from default local folders if not already present
    initialize_s3_cache_from_local()
    
    st.sidebar.markdown("<h4 style='color: white;'>📂 DATA SOURCE</h4>", unsafe_allow_html=True)
    
    source_key = f"{dashboard_key}_source"
    uploaded_file_key = f"{dashboard_key}_file"
    
    if source_key not in st.session_state:
        st.session_state[source_key] = "aws"
        
    # Sync AWS Button
    if st.sidebar.button("☁️ Sync AWS", use_container_width=True, help="Download latest Excel data from AWS S3"):
        with st.spinner("Downloading from S3..."):
            success, msg = sync_all_from_s3()
            if success:
                st.session_state[source_key] = "aws"
                st.sidebar.success("✅ Sync successful!")
            else:
                st.sidebar.error(f"❌ Sync failed: {msg}")
        st.rerun()
            
    # File Uploader representing [Upload Excel]
    uploaded_file = st.sidebar.file_uploader(
        "📤 Upload Excel",
        type=["xlsx"],
        help="Upload custom Excel dataset to render on this dashboard",
        key=uploaded_file_key
    )
    
    # If a file is uploaded, change the source to 'upload' automatically
    if uploaded_file is not None:
        if st.session_state[source_key] != "upload":
            st.session_state[source_key] = "upload"
            st.rerun()
            
    # If user clears the uploaded file in the UI, fall back to aws
    if uploaded_file is None and st.session_state[source_key] == "upload":
        st.session_state[source_key] = "aws"
        st.rerun()
        
    # Render active indicator
    active_source = st.session_state[source_key]
    if active_source == "aws":
        timestamp = get_last_sync_timestamp()
        st.sidebar.markdown(f"<div style='background-color:#0f2c59; color:white; padding:8px 12px; border-radius:6px; font-size:12px; font-weight:600; text-align:center;'>Mode: AWS S3 Cache<br/><span style='font-size:10px; opacity:0.8;'>Synced: {timestamp}</span></div>", unsafe_allow_html=True)
    elif active_source == "upload":
        st.sidebar.markdown("<div style='background-color:#20c997; color:white; padding:8px 12px; border-radius:6px; font-size:12px; font-weight:600; text-align:center;'>Mode: Uploaded Excel</div>", unsafe_allow_html=True)
    else:
        st.session_state[source_key] = "aws"
        st.rerun()
        
    return active_source
