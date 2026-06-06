"""
StayFlexi Booking Sync UI Module
Provides Streamlit interface for syncing bookings from StayFlexi to Supabase
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from stayflexi_integration import StayFlexiAPIConfig, StayFlexiAPIClient, StayFlexiDataSync
from log import log_activity

def show_stayflexi_sync():
    """Main interface for StayFlexi booking synchronization"""
    st.header("🏨 StayFlexi Booking Sync - Edenbeach")
    st.markdown("Synchronize bookings from StayFlexi Channel Manager to TIE System")
    st.markdown("---")
    
    # Initialize API Config
    api_config = StayFlexiAPIConfig()
    api_client = StayFlexiAPIClient(api_config)
    
    # Get Supabase client from session
    if 'supabase' not in st.session_state:
        st.error("❌ Supabase client not initialized. Please log in again.")
        return
    
    supabase = st.session_state.supabase
    data_sync = StayFlexiDataSync(api_client, supabase)
    
    # Tabs for different operations
    tab1, tab2, tab3, tab4 = st.tabs([
        "🔗 Connection Test", 
        "📥 Sync Bookings", 
        "📊 View Bookings", 
        "📈 Sync Status"
    ])
    
    # TAB 1: Connection Test
    with tab1:
        st.subheader("Test API Connection")
        st.write(f"**Base URL:** {api_config.api_base_url}")
        st.write(f"**PMS ID:** {api_config.pms_id}")
        st.write(f"**Hotel ID:** {api_config.hotel_id}")
        
        if st.button("🔍 Test Connection", key="test_connection"):
            with st.spinner("Testing connection..."):
                success, message = api_client.test_connection()
                if success:
                    st.success(message)
                    log_activity(supabase, st.session_state.username, "Tested StayFlexi API connection - SUCCESS")
                else:
                    st.error(message)
                    log_activity(supabase, st.session_state.username, f"Tested StayFlexi API connection - FAILED: {message}")
    
    # TAB 2: Sync Bookings
    with tab2:
        st.subheader("📥 Synchronize Bookings")
        
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "Start Date",
                value=datetime.now() - timedelta(days=30),
                key="sync_start_date"
            )
        with col2:
            end_date = st.date_input(
                "End Date",
                value=datetime.now() + timedelta(days=90),
                key="sync_end_date"
            )
        
        # Convert dates to StayFlexi format (DD-MM-YYYY)
        start_date_str = start_date.strftime("%d-%m-%Y")
        end_date_str = end_date.strftime("%d-%m-%Y")
        
        st.info(f"📅 Fetching bookings from {start_date_str} to {end_date_str}")
        
        if st.button("🚀 Start Sync", key="sync_bookings", use_container_width=True):
            with st.spinner("Synchronizing bookings..."):
                progress_bar = st.progress(0)
                
                # Fetch bookings from StayFlexi
                success, bookings, message = api_client.fetch_bookings(start_date_str, end_date_str)
                progress_bar.progress(50)
                
                if success:
                    st.success(f"✅ {message}")
                    
                    # Display fetched bookings
                    if bookings:
                        st.write(f"**Fetched {len(bookings)} bookings**")
                        
                        # Show sample data
                        if len(bookings) > 0:
                            st.write("**Sample Booking Data:**")
                            df = pd.DataFrame(bookings[:5])
                            st.dataframe(df, use_container_width=True)
                        
                        # Sync to Supabase
                        if st.button("✅ Confirm & Sync to Database", key="confirm_sync"):
                            with st.spinner("Syncing to database..."):
                                sync_result = data_sync.sync_bookings(start_date_str, end_date_str)
                                progress_bar.progress(100)
                                
                                if sync_result["success"]:
                                    st.success(f"✅ {sync_result['message']}")
                                    st.balloons()
                                    log_activity(
                                        supabase, 
                                        st.session_state.username, 
                                        f"Synced {sync_result['count']} bookings from StayFlexi"
                                    )
                                else:
                                    st.error(f"❌ {sync_result['message']}")
                                    log_activity(
                                        supabase, 
                                        st.session_state.username, 
                                        f"Failed to sync bookings: {sync_result['message']}"
                                    )
                    else:
                        st.info("ℹ️ No bookings found for the selected date range.")
                else:
                    st.error(f"❌ Failed to fetch bookings: {message}")
                    log_activity(
                        supabase, 
                        st.session_state.username, 
                        f"Failed to fetch bookings from StayFlexi: {message}"
                    )
    
    # TAB 3: View Bookings
    with tab3:
        st.subheader("📊 View Synced Bookings")
        
        try:
            # Fetch bookings from Supabase
            response = supabase.table("reservations").select("*").eq("source", "StayFlexi API").execute()
            
            if response.data:
                df = pd.DataFrame(response.data)
                
                # Filter columns for display
                display_columns = [
                    "booking_id", "guest_name", "email", "phone",
                    "checkin_date", "checkout_date", "status", "created_at"
                ]
                available_columns = [col for col in display_columns if col in df.columns]
                
                st.write(f"**Total StayFlexi Bookings: {len(df)}**")
                st.dataframe(df[available_columns], use_container_width=True)
                
                # Export option
                csv = df.to_csv(index=False)
                st.download_button(
                    label="📥 Download as CSV",
                    data=csv,
                    file_name=f"stayflexi_bookings_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
            else:
                st.info("ℹ️ No StayFlexi bookings found in database yet.")
        
        except Exception as e:
            st.error(f"❌ Error fetching bookings: {str(e)}")
    
    # TAB 4: Sync Status
    with tab4:
        st.subheader("📈 Synchronization Status")
        
        sync_status = data_sync.get_sync_status()
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Last Sync", sync_status["last_sync_formatted"])
        with col2:
            st.metric("Sync Status", "✅ OK" if sync_status["bookings"] else "⏳ Pending")
        with col3:
            st.metric("Error Count", sync_status["error_count"])
        with col4:
            st.metric("API Status", "🟢 Connected" if api_client.test_connection()[0] else "🔴 Disconnected")
        
        st.markdown("---")
        st.write("**API Configuration:**")
        config_info = {
            "Base URL": api_config.api_base_url,
            "PMS ID": api_config.pms_id,
            "Hotel ID": api_config.hotel_id,
            "Timeout": f"{api_config.timeout}s",
            "Max Retries": api_config.max_retries
        }
        
        for key, value in config_info.items():
            st.write(f"• **{key}:** {value}")


def show_booking_details(booking_id: str):
    """Show detailed view of a specific booking"""
    st.subheader(f"📋 Booking Details: {booking_id}")
    
    try:
        supabase = st.session_state.supabase
        response = supabase.table("reservations").select("*").eq("booking_id", booking_id).execute()
        
        if response.data:
            booking = response.data[0]
            
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Guest Information**")
                st.write(f"Name: {booking.get('guest_name', 'N/A')}")
                st.write(f"Email: {booking.get('email', 'N/A')}")
                st.write(f"Phone: {booking.get('phone', 'N/A')}")
            
            with col2:
                st.write("**Booking Information**")
                st.write(f"Status: {booking.get('status', 'N/A')}")
                st.write(f"Check-in: {booking.get('checkin_date', 'N/A')}")
                st.write(f"Check-out: {booking.get('checkout_date', 'N/A')}")
            
            st.write("**Room Details**")
            st.write(f"Room Type: {booking.get('room_type', 'N/A')}")
            st.write(f"Guests: {booking.get('number_of_guests', 'N/A')}")
            st.write(f"Total Price: {booking.get('total_price', 'N/A')}")
            
            if booking.get('notes'):
                st.write("**Notes**")
                st.write(booking['notes'])
        
        else:
            st.warning(f"Booking {booking_id} not found.")
    
    except Exception as e:
        st.error(f"Error fetching booking details: {str(e)}")
