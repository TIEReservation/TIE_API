"""
Streamlit UI for Eden Beach API Integration
Provides configuration interface and sync controls
"""

import streamlit as st
from datetime import datetime
import json
from eden_beach_integration import (
    EdenBeachAPIConfig,
    EdenBeachAPIClient,
    EdenBeachDataSync
)


def initialize_eden_beach_session():
    """Initialize session state for Eden Beach integration"""
    if "eden_beach_config" not in st.session_state:
        st.session_state.eden_beach_config = EdenBeachAPIConfig()
    
    if "eden_beach_client" not in st.session_state:
        st.session_state.eden_beach_client = None
    
    if "eden_beach_sync" not in st.session_state:
        st.session_state.eden_beach_sync = None
    
    if "eden_beach_api_key" not in st.session_state:
        st.session_state.eden_beach_api_key = ""
    
    if "eden_beach_api_url" not in st.session_state:
        st.session_state.eden_beach_api_url = ""
    
    if "eden_beach_last_sync" not in st.session_state:
        st.session_state.eden_beach_last_sync = None


def show_api_configuration():
    """Display API configuration interface"""
    st.header("🏖️ Eden Beach Resort - API Configuration")
    
    initialize_eden_beach_session()
    
    with st.expander("📋 API Settings", expanded=True):
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("1️⃣ Enter API Key")
            api_key = st.text_input(
                "API Key",
                type="password",
                value=st.session_state.eden_beach_api_key,
                key="eden_beach_api_key_input",
                help="Enter your Eden Beach API key"
            )
            st.caption("🔒 Your API key is securely stored in session")
        
        with col2:
            st.subheader("2️⃣ Enter API Base URL")
            api_url = st.text_input(
                "API Base URL",
                value=st.session_state.eden_beach_api_url,
                key="eden_beach_api_url_input",
                placeholder="https://api.edenbeach.com",
                help="e.g., https://api.edenbeach.com"
            )
            st.caption("Make sure to include https://")
    
    # Save configuration
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("💾 Save Configuration", use_container_width=True):
            if not api_key or not api_url:
                st.error("❌ Both API Key and URL are required!")
            else:
                try:
                    st.session_state.eden_beach_config.set_api_key(api_key)
                    st.session_state.eden_beach_config.set_api_url(api_url)
                    st.session_state.eden_beach_api_key = api_key
                    st.session_state.eden_beach_api_url = api_url
                    
                    # Initialize client
                    st.session_state.eden_beach_client = EdenBeachAPIClient(
                        st.session_state.eden_beach_config
                    )
                    
                    # Initialize sync manager (requires supabase from parent)
                    if hasattr(st, 'session_state') and 'supabase' in dir(st.session_state):
                        from app import supabase
                        st.session_state.eden_beach_sync = EdenBeachDataSync(
                            st.session_state.eden_beach_client,
                            supabase
                        )
                    
                    st.success("✅ Configuration saved successfully!")
                except ValueError as e:
                    st.error(f"❌ Configuration error: {str(e)}")
                except Exception as e:
                    st.error(f"❌ Unexpected error: {str(e)}")
    
    with col2:
        if st.button("🔗 Test Connection", use_container_width=True):
            if st.session_state.eden_beach_client is None:
                st.warning("⚠️ Please save configuration first")
            else:
                with st.spinner("Testing connection..."):
                    success, message = st.session_state.eden_beach_client.test_connection()
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
    
    with col3:
        if st.button("🔄 Reset Configuration", use_container_width=True):
            st.session_state.eden_beach_api_key = ""
            st.session_state.eden_beach_api_url = ""
            st.session_state.eden_beach_config = EdenBeachAPIConfig()
            st.session_state.eden_beach_client = None
            st.session_state.eden_beach_sync = None
            st.success("✅ Configuration reset")
            st.rerun()


def show_sync_controls(supabase):
    """Display sync control interface with buttons and status"""
    st.header("🔄 Data Synchronization")
    
    initialize_eden_beach_session()
    
    if st.session_state.eden_beach_client is None:
        st.warning("⚠️ Please configure API connection first")
        return
    
    if st.session_state.eden_beach_sync is None:
        st.session_state.eden_beach_sync = EdenBeachDataSync(
            st.session_state.eden_beach_client,
            supabase
        )
    
    # Sync options
    st.subheader("📊 Choose what to sync")
    
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    
    with col1:
        if st.button("📅 Sync Bookings", use_container_width=True, key="sync_bookings"):
            with st.spinner("Syncing bookings..."):
                result = st.session_state.eden_beach_sync.sync_bookings()
                if result["success"]:
                    st.success(f"✅ {result['message']}")
                    st.session_state.eden_beach_last_sync = datetime.now()
                else:
                    st.error(f"❌ {result['message']}")
    
    with col2:
        if st.button("👥 Sync Guests", use_container_width=True, key="sync_guests"):
            with st.spinner("Syncing guests..."):
                result = st.session_state.eden_beach_sync.sync_guests()
                if result["success"]:
                    st.success(f"✅ {result['message']}")
                    st.session_state.eden_beach_last_sync = datetime.now()
                else:
                    st.error(f"❌ {result['message']}")
    
    with col3:
        if st.button("🏠 Sync Rooms", use_container_width=True, key="sync_rooms"):
            with st.spinner("Syncing rooms..."):
                result = st.session_state.eden_beach_sync.sync_rooms()
                if result["success"]:
                    st.success(f"✅ {result['message']}")
                    st.session_state.eden_beach_last_sync = datetime.now()
                else:
                    st.error(f"❌ {result['message']}")
    
    with col4:
        if st.button("🔄 Sync All", use_container_width=True, key="sync_all"):
            with st.spinner("Syncing all data..."):
                results = st.session_state.eden_beach_sync.sync_all()
                
                st.subheader("Sync Results:")
                
                # Display bookings sync result
                if results["bookings"]["success"]:
                    st.success(f"✅ Bookings: {results['bookings']['message']}")
                else:
                    st.error(f"❌ Bookings: {results['bookings']['message']}")
                
                # Display guests sync result
                if results["guests"]["success"]:
                    st.success(f"✅ Guests: {results['guests']['message']}")
                else:
                    st.error(f"❌ Guests: {results['guests']['message']}")
                
                # Display rooms sync result
                if results["rooms"]["success"]:
                    st.success(f"✅ Rooms: {results['rooms']['message']}")
                else:
                    st.error(f"❌ Rooms: {results['rooms']['message']}")
                
                st.session_state.eden_beach_last_sync = datetime.now()
    
    st.markdown("---")
    
    # Sync status
    st.subheader("📈 Sync Status")
    
    if st.session_state.eden_beach_sync:
        status = st.session_state.eden_beach_sync.get_sync_status()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Bookings Synced",
                "✅" if status["bookings"] else "⏳",
                help="Bookings synchronization status"
            )
        
        with col2:
            st.metric(
                "Guests Synced",
                "✅" if status["guests"] else "⏳",
                help="Guests synchronization status"
            )
        
        with col3:
            st.metric(
                "Rooms Synced",
                "✅" if status["rooms"] else "⏳",
                help="Rooms synchronization status"
            )
        
        with col4:
            st.metric(
                "Errors",
                status["error_count"],
                help="Total errors during sync"
            )
        
        st.info(f"⏱️ Last sync: {status['last_sync_formatted']}")


def show_booking_fetch_interface(supabase):
    """Fetch and display bookings from Eden Beach API"""
    st.header("📥 Fetch Bookings from Eden Beach")
    
    initialize_eden_beach_session()
    
    if st.session_state.eden_beach_client is None:
        st.warning("⚠️ Please configure API connection first")
        return
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        start_date = st.date_input("Start Date", key="eden_beach_start_date")
    
    with col2:
        end_date = st.date_input("End Date", key="eden_beach_end_date")
    
    if st.button("🔍 Fetch Bookings", use_container_width=True):
        with st.spinner("Fetching bookings..."):
            success, bookings, message = st.session_state.eden_beach_client.fetch_bookings(
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat()
            )
            
            if success and bookings:
                st.success(message)
                
                # Display bookings in table
                st.subheader(f"📊 {len(bookings)} Booking(s) Found")
                
                # Create DataFrame for display
                import pandas as pd
                df = pd.DataFrame(bookings)
                
                # Display with pagination
                st.dataframe(df, use_container_width=True)
                
                # Option to import to Supabase
                if st.button("📤 Import to Supabase", key="import_eden_bookings"):
                    with st.spinner("Importing bookings..."):
                        if st.session_state.eden_beach_sync:
                            result = st.session_state.eden_beach_sync.sync_bookings()
                            if result["success"]:
                                st.success(f"✅ {result['message']}")
                            else:
                                st.error(f"❌ {result['message']}")
            else:
                st.error(f"❌ {message}")


def show_eden_beach_page(supabase):
    """Main page for Eden Beach integration"""
    st.set_page_config(
        page_title="Eden Beach Integration",
        page_icon="🏖️",
        layout="wide"
    )
    
    st.title("🏖️ Eden Beach Resort - Integration Hub")
    st.markdown("---")
    
    # Tabs for different sections
    tab1, tab2, tab3 = st.tabs(["Configuration", "Synchronization", "Fetch Data"])
    
    with tab1:
        show_api_configuration()
    
    with tab2:
        show_sync_controls(supabase)
    
    with tab3:
        show_booking_fetch_interface(supabase)
    
    st.markdown("---")
    st.subheader("ℹ️ Help & Information")
    
    with st.expander("How to use this integration"):
        st.markdown("""
        ### Step 1: Configure API Connection
        - Enter your Eden Beach API Key
        - Enter the API Base URL
        - Click "Test Connection" to verify
        
        ### Step 2: Synchronize Data
        - Choose what data to sync (Bookings, Guests, Rooms)
        - Or sync everything at once with "Sync All"
        - Monitor the status of each sync operation
        
        ### Step 3: Fetch Specific Data
        - Use the "Fetch Data" tab to retrieve bookings for a date range
        - Review the data before importing to Supabase
        - Import directly to your database
        
        ### Troubleshooting
        - 🔗 **Connection issues?** Check your API key and URL
        - ⏱️ **Timeout?** Your network might be slow; try again
        - 🔑 **Auth error?** Verify your API credentials with Eden Beach support
        """)
    
    with st.expander("API Documentation"):
        st.markdown("""
        ### Available Endpoints
        - `GET /api/health` - Test connection
        - `GET /api/bookings` - Fetch all bookings
        - `GET /api/bookings/{id}` - Get booking details
        - `GET /api/availability` - Check room availability
        - `POST /api/bookings` - Create new booking
        - `PUT /api/bookings/{id}` - Update booking
        - `GET /api/guests` - Fetch guest information
        - `GET /api/rooms` - Fetch room inventory
        """)


# Export functions
__all__ = [
    'initialize_eden_beach_session',
    'show_api_configuration',
    'show_sync_controls',
    'show_booking_fetch_interface',
    'show_eden_beach_page'
]
