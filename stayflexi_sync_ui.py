"""
Streamlit UI for Stayflexi Sync Integration
Allows manual sync of Eden Beach bookings from Stayflexi to local database
"""

import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
from stayflexi_sync import (
    StayflexiSyncConfig,
    StayflexiAPIClient,
    LocalDatabaseSync
)


def initialize_stayflexi_session():
    """Initialize session state for Stayflexi sync"""
    if "stayflexi_config" not in st.session_state:
        st.session_state.stayflexi_config = StayflexiSyncConfig()
    
    if "stayflexi_client" not in st.session_state:
        st.session_state.stayflexi_client = None
    
    if "stayflexi_sync" not in st.session_state:
        st.session_state.stayflexi_sync = None
    
    if "stayflexi_api_token" not in st.session_state:
        st.session_state.stayflexi_api_token = ""
    
    if "stayflexi_email" not in st.session_state:
        st.session_state.stayflexi_email = ""


def show_stayflexi_quick_sync_button(supabase):
    """
    Quick Stayflexi sync button for Online Reservations page
    Add this button at the top of the online reservations page
    """
    initialize_stayflexi_session()
    
    # Store credentials in session
    if "stayflexi_stored_token" not in st.session_state:
        st.session_state.stayflexi_stored_token = ""
    if "stayflexi_stored_email" not in st.session_state:
        st.session_state.stayflexi_stored_email = ""
    
    # Compact button row
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        st.markdown("**🔄 Sync from Stayflexi for Eden Beach Resort**")
    
    with col2:
        if st.button("⚙️ Setup", use_container_width=True, key="stayflexi_setup_btn"):
            st.session_state.show_stayflexi_setup = True
    
    with col3:
        if st.button("🔄 Sync Now", use_container_width=True, key="stayflexi_quick_sync_btn"):
            if not st.session_state.stayflexi_stored_token or not st.session_state.stayflexi_stored_email:
                st.warning("⚠️ Please setup Stayflexi credentials first")
            else:
                with st.spinner("Syncing from Stayflexi..."):
                    try:
                        config = StayflexiSyncConfig()
                        config.set_credentials(st.session_state.stayflexi_stored_token, st.session_state.stayflexi_stored_email)
                        client = StayflexiAPIClient(config)
                        sync = LocalDatabaseSync(client, supabase)
                        
                        # Get date range (last 30 days to future)
                        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
                        end_date = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")
                        
                        result = sync.sync_bookings(start_date, end_date)
                        
                        if result["success"]:
                            st.success(result["message"])
                            
                            # Show sync results
                            col_a, col_b, col_c = st.columns(3)
                            with col_a:
                                st.metric("✅ Imported", result["imported"])
                            with col_b:
                                st.metric("⏭️ Skipped (Duplicates)", result["skipped"])
                            with col_c:
                                st.metric("❌ Errors", result["errors"])
                            
                            # Show sync log
                            if result["log"]:
                                with st.expander("📋 Sync Details"):
                                    for log_entry in result["log"][:20]:  # Show first 20
                                        st.text(log_entry)
                                    if len(result["log"]) > 20:
                                        st.info(f"... and {len(result['log']) - 20} more entries")
                            
                            st.rerun()
                        else:
                            st.error(f"❌ Sync failed: {result['message']}")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
    
    # Setup panel (only show if clicked)
    if st.session_state.get("show_stayflexi_setup", False):
        st.markdown("---")
        with st.expander("⚙️ Stayflexi Setup", expanded=True):
            col_token, col_email = st.columns([1, 1])
            
            with col_token:
                api_token = st.text_input(
                    "Stayflexi API Token",
                    type="password",
                    key="setup_stayflexi_token",
                    placeholder="Enter your API token"
                )
            
            with col_email:
                email = st.text_input(
                    "Stayflexi Email",
                    key="setup_stayflexi_email",
                    placeholder="your@email.com"
                )
            
            col_save, col_test, col_close = st.columns(3)
            
            with col_save:
                if st.button("💾 Save & Connect", use_container_width=True):
                    if not api_token or not email:
                        st.error("❌ Please enter both fields")
                    else:
                        try:
                            config = StayflexiSyncConfig()
                            config.set_credentials(api_token, email)
                            client = StayflexiAPIClient(config)
                            
                            with st.spinner("Testing connection..."):
                                success, message = client.test_connection()
                                if success:
                                    st.session_state.stayflexi_stored_token = api_token
                                    st.session_state.stayflexi_stored_email = email
                                    st.success(message)
                                else:
                                    st.error(message)
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")
            
            with col_test:
                if st.button("🔗 Test Connection", use_container_width=True):
                    if not api_token or not email:
                        st.warning("⚠️ Please enter credentials first")
                    else:
                        try:
                            config = StayflexiSyncConfig()
                            config.set_credentials(api_token, email)
                            client = StayflexiAPIClient(config)
                            
                            with st.spinner("Testing..."):
                                success, message = client.test_connection()
                                if success:
                                    st.success(message)
                                else:
                                    st.error(message)
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")
            
            with col_close:
                if st.button("✓ Done", use_container_width=True):
                    st.session_state.show_stayflexi_setup = False
                    st.rerun()
