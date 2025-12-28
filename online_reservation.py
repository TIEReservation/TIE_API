import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
import re
import requests
import time
from supabase import create_client, Client
from utils import safe_int, safe_float, get_property_name

# Initialize Supabase client
try:
    supabase: Client = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
except KeyError as e:
    st.error(f"Missing Supabase secret: {e}. Please check Streamlit Cloud secrets configuration.")
    st.stop()

# Stayflexi API Configuration
STAYFLEXI_API_BASE_URL = "https://api.stayflexi.com"
STAYFLEXI_API_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJnYXlhdGhyaS50aWVAZ21haWwuY29tIiwiaXNzIjoibWF5YW5rU0YiLCJpYXQiOjE3NTQ0ODE4MjQsImV4cCI6MTc4NTU4NTgyNH0.9UmdbaCu7P5_Mfm8nIAaT2MDLR_RyTx3RdouMC0dP0o"

# Property mapping from hotel_id to property name
PROPERTY_MAPPING = {
    "4077": "Le Poshe Beach view",
    "4078": "La Millionaire Resort",
    "4079": "Le Poshe Luxury",
    "4080": "Le Poshe Suite",
    "4081": "La Paradise Residency",
    "4082": "La Paradise Luxury",
    "4083": "La Villa Heritage",
    "4084": "Le Pondy Beachside",
    "4085": "Le Royce Villa",
    "4086": "La Tamara Luxury",
    "4087": "La Antilia Luxury",
    "4088": "La Tamara Suite",
    "4089": "Le Park Resort",
    "4090": "Villa Shakti",
    "4091": "Eden Beach Resort",
    "4092": "La Coromandel Luxury",
    "4093": "Le Terra",
    "4094": "Happymates Forest Retreat"
}

def parse_date(dt_str):
    """Parse date string with or without time."""
    if not dt_str or pd.isna(dt_str):
        return None
    try:
        return datetime.strptime(dt_str, "%d/%m/%Y %H:%M:%S").date()
    except ValueError:
        try:
            return datetime.strptime(dt_str, "%d/%m/%Y").date()
        except ValueError:
            return None

def parse_stayflexi_date(date_str):
    """Parse Stayflexi API date format."""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
    except:
        try:
            return datetime.strptime(date_str[:10], "%Y-%m-%d").date()
        except:
            return None

def parse_pax(pax_str):
    """Parse pax string to get adults, children, infants."""
    adults = 0
    children = 0
    infants = 0
    if not pax_str or pd.isna(pax_str):
        return adults, children, infants
    pax_str = re.sub(r'\s*,\s*', ',', pax_str)
    parts = pax_str.split(',')
    for part in parts:
        part = part.strip()
        if 'Adults:' in part:
            try:
                adults += int(part.split('Adults:')[1].strip())
            except ValueError:
                pass
        elif 'Children:' in part:
            try:
                children += int(part.split('Children:')[1].strip())
            except ValueError:
                pass
        elif 'Infant:' in part:
            try:
                infants += int(part.split('Infant:')[1].strip())
            except ValueError:
                pass
    return adults, children, infants

def truncate_string(value, max_length=50):
    """Truncate string to specified length."""
    if not value:
        return value
    return str(value)[:max_length] if len(str(value)) > max_length else str(value)

def calculate_payment_status(total_payment: float, booking_amount: float) -> str:
    """Calculate payment status based on amounts."""
    if total_payment >= booking_amount:
        return "Fully Paid"
    elif total_payment > 0:
        return "Partially Paid"
    else:
        return "Not Paid"

def insert_online_reservation(reservation):
    """Insert a new online reservation into Supabase."""
    try:
        truncated_reservation = reservation.copy()
        
        string_fields_50 = [
            "property", "booking_id", "guest_name", "guest_phone", "room_no", 
            "room_type", "rate_plans", "booking_source", "segment", "staflexi_status",
            "mode_of_booking", "booking_status", "payment_status", "submitted_by", "modified_by"
        ]
        
        for field in string_fields_50:
            if field in truncated_reservation:
                truncated_reservation[field] = truncate_string(truncated_reservation[field], 50)
        
        if "remarks" in truncated_reservation:
            truncated_reservation["remarks"] = truncate_string(truncated_reservation["remarks"], 500)
        
        response = supabase.table("online_reservations").insert(truncated_reservation).execute()
        return bool(response.data)
    except Exception as e:
        if '23505' in str(e) and 'duplicate key value' in str(e).lower():
            return False
        st.error(f"Error inserting online reservation: {e}")
        return False

def load_online_reservations_from_supabase():
    """Load online reservations from Supabase."""
    try:
        response = supabase.table("online_reservations").select("*").order("check_in", desc=True).execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"Error loading online reservations: {e}")
        return []

def get_existing_booking_ids():
    """Get all existing booking IDs from database."""
    try:
        response = supabase.table("online_reservations").select("booking_id").execute()
        return {r["booking_id"] for r in response.data if r.get("booking_id")}
    except Exception as e:
        st.error(f"Error fetching existing booking IDs: {e}")
        return set()

def fetch_stayflexi_bookings(hotel_id: str, from_date: date, to_date: date):
    """Fetch bookings from Stayflexi API for a specific property and date range."""
    url = f"{STAYFLEXI_API_BASE_URL}/core/api/v1/reservation/navigationGetRoomBookings"
    
    headers = {
        "Authorization": f"Bearer {STAYFLEXI_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "hotelId": hotel_id,
        "from": from_date.strftime("%Y-%m-%d"),
        "to": to_date.strftime("%Y-%m-%d")
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if isinstance(data, dict) and "bookings" in data:
            return data["bookings"]
        elif isinstance(data, list):
            return data
        else:
            return []
            
    except requests.exceptions.RequestException as e:
        st.warning(f"API Request Failed for hotel {hotel_id}: {e}")
        return []
    except Exception as e:
        st.warning(f"Error fetching bookings for hotel {hotel_id}: {e}")
        return []

def transform_stayflexi_to_db_format(booking: dict, property_name: str):
    """Transform Stayflexi booking data to match database schema."""
    guest_name = truncate_string(
        booking.get("customer_name") or booking.get("guestName") or booking.get("name", ""),
        50
    )
    guest_phone = truncate_string(
        booking.get("customer_phone") or booking.get("phone") or booking.get("mobile", ""),
        50
    )
    
    check_in = parse_stayflexi_date(booking.get("checkin") or booking.get("checkIn"))
    check_out = parse_stayflexi_date(booking.get("checkout") or booking.get("checkOut"))
    booking_made_on = parse_stayflexi_date(
        booking.get("booking_made_on") or booking.get("bookingDate") or booking.get("created_at")
    )
    
    no_of_adults = int(booking.get("adults", 0) or booking.get("no_of_adults", 0))
    no_of_children = int(booking.get("children", 0) or booking.get("no_of_children", 0))
    no_of_infant = int(booking.get("infants", 0) or booking.get("no_of_infant", 0))
    total_pax = no_of_adults + no_of_children + no_of_infant
    
    room_no = truncate_string(
        booking.get("room_ids") or booking.get("roomNumber") or booking.get("room_no", ""),
        50
    )
    room_type = truncate_string(
        booking.get("room_types") or booking.get("roomType") or booking.get("room_type", ""),
        50
    )
    
    booking_id = truncate_string(booking.get("booking_id") or booking.get("id", ""), 50)
    booking_source = truncate_string(
        booking.get("booking_source") or booking.get("source", ""),
        50
    )
    segment = truncate_string(booking.get("segment", ""), 50)
    staflexi_status = truncate_string(booking.get("status", ""), 50)
    rate_plans = truncate_string(booking.get("rate_plans") or booking.get("ratePlan", ""), 50)
    
    booking_amount = float(booking.get("booking_amount") or booking.get("totalAmount", 0))
    total_payment_made = float(booking.get("Total Payment Made") or booking.get("paidAmount", 0))
    balance_due = float(booking.get("balance_due") or (booking_amount - total_payment_made))
    
    total_amount_with_services = float(booking.get("total_amount_with_services", 0))
    ota_gross_amount = float(booking.get("ota_gross_amount", 0))
    ota_commission = float(booking.get("ota_commission", 0))
    ota_tax = float(booking.get("ota_tax", 0))
    ota_net_amount = float(booking.get("ota_net_amount", 0))
    room_revenue = float(booking.get("room_revenue", 0))
    
    room_nights = 0
    if check_in and check_out:
        room_nights = (check_out - check_in).days
    
    mode_of_booking = truncate_string(booking_source, 50)
    booking_status = "Pending"
    payment_status = calculate_payment_status(total_payment_made, booking_amount)
    
    remarks = truncate_string(
        booking.get("special_requests") or booking.get("remarks") or booking.get("notes", ""),
        500
    )
    
    db_record = {
        "property": property_name,
        "booking_id": booking_id,
        "booking_made_on": str(booking_made_on) if booking_made_on else None,
        "guest_name": guest_name,
        "guest_phone": guest_phone,
        "check_in": str(check_in) if check_in else None,
        "check_out": str(check_out) if check_out else None,
        "no_of_adults": no_of_adults,
        "no_of_children": no_of_children,
        "no_of_infant": no_of_infant,
        "total_pax": total_pax,
        "room_no": room_no,
        "room_type": room_type,
        "rate_plans": rate_plans,
        "booking_source": booking_source,
        "segment": segment,
        "staflexi_status": staflexi_status,
        "booking_confirmed_on": None,
        "booking_amount": booking_amount,
        "total_payment_made": total_payment_made,
        "balance_due": balance_due,
        "mode_of_booking": mode_of_booking,
        "booking_status": booking_status,
        "payment_status": payment_status,
        "remarks": remarks,
        "submitted_by": "Stayflexi API",
        "modified_by": "",
        "total_amount_with_services": total_amount_with_services,
        "ota_gross_amount": ota_gross_amount,
        "ota_commission": ota_commission,
        "ota_tax": ota_tax,
        "ota_net_amount": ota_net_amount,
        "room_revenue": room_revenue,
        "room_nights": room_nights,
        "advance_mop": "",
        "balance_mop": "",
        "advance_remarks": "",
        "balance_remarks": "",
        "accounts_status": "Pending"
    }
    
    return db_record

def sync_property_bookings(hotel_id: str, property_name: str, from_date: date, to_date: date, existing_ids: set):
    """Sync bookings for a single property. Returns (inserted, skipped, errors)"""
    inserted = 0
    skipped = 0
    errors = 0
    
    api_bookings = fetch_stayflexi_bookings(hotel_id, from_date, to_date)
    
    if not api_bookings:
        return inserted, skipped, errors
    
    for booking in api_bookings:
        try:
            db_record = transform_stayflexi_to_db_format(booking, property_name)
            
            if db_record["booking_id"] in existing_ids:
                skipped += 1
                continue
            
            if insert_online_reservation(db_record):
                inserted += 1
                existing_ids.add(db_record["booking_id"])
            else:
                skipped += 1
                
        except Exception as e:
            st.warning(f"Error processing booking: {e}")
            errors += 1
    
    return inserted, skipped, errors

def process_and_sync_excel(uploaded_file):
    """Process the uploaded Excel file and sync to DB."""
    try:
        df = pd.read_excel(uploaded_file, header=0)
        if df.empty:
            st.warning("Uploaded file is empty.")
            return 0, 0
        
        existing_reservations = load_online_reservations_from_supabase()
        existing_ids = {r["booking_id"] for r in existing_reservations}
        inserted = 0
        skipped = 0
        
        for _, row in df.iterrows():
            hotel_id = str(safe_int(row.get("hotel id", "")))
            property_name = get_property_name(hotel_id)
            if property_name == "Unknown Property":
                property_name = str(row.get("hotel name", "")).split("-")[0].strip() if row.get("hotel name") else ""
            
            booking_id = str(row.get("booking id", ""))
            if not booking_id:
                continue
            if booking_id in existing_ids:
                skipped += 1
                continue
            
            booking_made_on = parse_date(row.get("booking_made_on"))
            guest_name = truncate_string(row.get("customer_name", ""), 50)
            guest_phone = truncate_string(row.get("customer_phone", ""), 50)
            check_in = parse_date(row.get("checkin"))
            check_out = parse_date(row.get("checkout"))
            pax_str = str(row.get("pax", ""))
            no_of_adults, no_of_children, no_of_infant = parse_pax(pax_str)
            total_pax = no_of_adults + no_of_children + no_of_infant
            room_no = truncate_string(row.get("room ids", ""), 50)
            room_type = truncate_string(row.get("room types", ""), 50)
            rate_plans = truncate_string(row.get("rate_plans", ""), 50)
            booking_source = truncate_string(row.get("booking_source", ""), 50)
            segment = truncate_string(row.get("segment", ""), 50)
            staflexi_status = truncate_string(row.get("status", ""), 50)
            booking_confirmed_on = None
            booking_amount = safe_float(row.get("booking_amount"))
            total_payment_made = safe_float(row.get("Total Payment Made"))
            balance_due = safe_float(row.get("balance_due"))
            mode_of_booking = truncate_string(booking_source, 50)
            booking_status = "Pending"
            
            if total_payment_made >= booking_amount:
                payment_status = "Fully Paid"
            elif total_payment_made > 0:
                payment_status = "Partially Paid"
            else:
                payment_status = "Not Paid"
            
            remarks = truncate_string(row.get("special_requests", ""), 500)
            submitted_by = ""
            modified_by = ""
            total_amount_with_services = safe_float(row.get("total_amount_with_services"))
            ota_gross_amount = safe_float(row.get("ota_gross_amount"))
            ota_commission = safe_float(row.get("ota_commission"))
            ota_tax = safe_float(row.get("ota_tax"))
            ota_net_amount = safe_float(row.get("ota_net_amount"))
            room_revenue = safe_float(row.get("room_revenue"))
            
            reservation = {
                "property": property_name,
                "booking_id": booking_id,
                "booking_made_on": str(booking_made_on) if booking_made_on else None,
                "guest_name": guest_name,
                "guest_phone": guest_phone,
                "check_in": str(check_in) if check_in else None,
                "check_out": str(check_out) if check_out else None,
                "no_of_adults": no_of_adults,
                "no_of_children": no_of_children,
                "no_of_infant": no_of_infant,
                "total_pax": total_pax,
                "room_no": room_no,
                "room_type": room_type,
                "rate_plans": rate_plans,
                "booking_source": booking_source,
                "segment": segment,
                "staflexi_status": staflexi_status,
                "booking_confirmed_on": booking_confirmed_on,
                "booking_amount": booking_amount,
                "total_payment_made": total_payment_made,
                "balance_due": balance_due,
                "mode_of_booking": mode_of_booking,
                "booking_status": booking_status,
                "payment_status": payment_status,
                "remarks": remarks,
                "submitted_by": submitted_by,
                "modified_by": modified_by,
                "total_amount_with_services": total_amount_with_services,
                "ota_gross_amount": ota_gross_amount,
                "ota_commission": ota_commission,
                "ota_tax": ota_tax,
                "ota_net_amount": ota_net_amount,
                "room_revenue": room_revenue
            }
            
            if insert_online_reservation(reservation):
                inserted += 1
                st.session_state.online_reservations.append(reservation)
        
        return inserted, skipped
    except Exception as e:
        st.error(f"Error processing Excel file: {e}")
        return 0, 0

def show_online_reservations():
    """Display online reservations page with upload, API sync, and view."""
    st.title("📥 Online Reservations")
    
    if 'online_reservations' not in st.session_state:
        st.session_state.online_reservations = load_online_reservations_from_supabase()

    # Create tabs for different sync methods
    tab1, tab2 = st.tabs(["📄 Excel Upload", "🔄 Stayflexi API Sync"])
    
    # Tab 1: Excel Upload
    with tab1:
        st.subheader("Upload and Sync Excel File")
        uploaded_file = st.file_uploader("Choose an Excel file", type="xlsx")
        if uploaded_file is not None:
            if st.button("📄 Sync Excel to Database", key="sync_excel"):
                with st.spinner("Processing and syncing..."):
                    inserted, skipped = process_and_sync_excel(uploaded_file)
                    st.success(f"✅ Synced successfully! Inserted: {inserted}, Skipped (duplicates): {skipped}")
                    st.session_state.online_reservations = load_online_reservations_from_supabase()
    
    # Tab 2: Stayflexi API Sync
    with tab2:
        st.subheader("Sync from Stayflexi API")
        st.markdown("""
        Automatically fetch bookings from Stayflexi API for all properties.
        All synced bookings will appear in DMS (Daily Management Status).
        """)
        
        col1, col2 = st.columns(2)
        with col1:
            from_date = st.date_input(
                "From Date",
                value=date.today() - timedelta(days=7),
                max_value=date.today() + timedelta(days=365),
                key="api_from_date"
            )
        with col2:
            to_date = st.date_input(
                "To Date",
                value=date.today() + timedelta(days=30),
                max_value=date.today() + timedelta(days=365),
                key="api_to_date"
            )
        
        if from_date > to_date:
            st.error("From Date cannot be after To Date")
        else:
            sync_all = st.checkbox("Sync All Properties", value=True, key="sync_all_props")
            
            selected_properties = []
            if not sync_all:
                selected_properties = st.multiselect(
                    "Select Properties",
                    options=list(PROPERTY_MAPPING.values()),
                    default=list(PROPERTY_MAPPING.values()),
                    key="select_props"
                )
            
            col1, col2 = st.columns([1, 3])
            with col1:
                if st.button("🔄 Sync from API", use_container_width=True, type="primary", key="sync_api"):
                    if not sync_all and not selected_properties:
                        st.error("Please select at least one property to sync")
                    else:
                        with st.spinner("Syncing bookings from Stayflexi API..."):
                            existing_ids = get_existing_booking_ids()
                            
                            total_inserted = 0
                            total_skipped = 0
                            total_errors = 0
                            property_results = {}
                            
                            if sync_all:
                                properties_to_sync = PROPERTY_MAPPING.items()
                            else:
                                properties_to_sync = [
                                    (hid, pname) for hid, pname in PROPERTY_MAPPING.items()
                                    if pname in selected_properties
                                ]
                            
                            progress_bar = st.progress(0)
                            status_text = st.empty()
                            total_properties = len(properties_to_sync)
                            
                            for idx, (hotel_id, property_name) in enumerate(properties_to_sync):
                                status_text.text(f"Syncing {property_name}... ({idx + 1}/{total_properties})")
                                
                                inserted, skipped, errors = sync_property_bookings(
                                    hotel_id, property_name, from_date, to_date, existing_ids
                                )
                                
                                total_inserted += inserted
                                total_skipped += skipped
                                total_errors += errors
                                
                                property_results[property_name] = {
                                    "inserted": inserted,
                                    "skipped": skipped,
                                    "errors": errors
                                }
                                
                                progress_bar.progress((idx + 1) / total_properties)
                                time.sleep(0.5)
                            
                            progress_bar.empty()
                            status_text.empty()
                            
                            st.success(f"✅ API Sync Complete!")
                            
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("✅ Inserted", total_inserted)
                            with col2:
                                st.metric("⏭️ Skipped", total_skipped)
                            with col3:
                                st.metric("❌ Errors", total_errors)
                            
                            if property_results:
                                st.subheader("Details by Property")
                                results_df = pd.DataFrame.from_dict(property_results, orient='index')
                                results_df = results_df.reset_index()
                                results_df.columns = ["Property", "Inserted", "Skipped", "Errors"]
                                results_df = results_df[(results_df["Inserted"] > 0) | (results_df["Skipped"] > 0) | (results_df["Errors"] > 0)]
                                if not results_df.empty:
                                    st.dataframe(results_df, use_container_width=True)
                            
                            if 'online_reservations' in st.session_state:
                                del st.session_state.online_reservations
                            st.session_state.online_reservations = load_online_reservations_from_supabase()
                            
                            st.info("💡 Synced bookings will now appear in DMS and can be edited in 'Edit Online Reservations'")
            
            with st.expander("ℹ️ API Sync Information"):
                st.markdown("""
                **How It Works:**
                1. Fetches bookings from Stayflexi API for selected date range
                2. Transforms data to match your database schema
                3. Skips duplicate booking IDs automatically
                4. Inserts new bookings with status "Pending"
                5. Bookings automatically appear in DMS
                
                **Default Settings:**
                - Booking Status: "Pending" (update manually if needed)
                - Payment Status: Calculated automatically
                - Submitted By: "Stayflexi API"
                
                **Property Mapping:**
                """)
                mapping_df = pd.DataFrame(
                    list(PROPERTY_MAPPING.items()),
                    columns=["Hotel ID", "Property Name"]
                )
                st.dataframe(mapping_df, use_container_width=True, height=300)

    # View section
    st.markdown("---")
    st.subheader("View Online Reservations")
    
    if not st.session_state.online_reservations:
        st.info("No online reservations available.")
        return

    df = pd.DataFrame(st.session_state.online_reservations)
    
    st.subheader("Filters")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        start_date = st.date_input("Start Date (Check-In)", value=None, key="view_start_date")
    with col2:
        end_date = st.date_input("End Date (Check-In)", value=None, key="view_end_date")
    with col3:
        filter_status = st.selectbox(
            "Filter by Booking Status", 
            ["All", "Pending", "Follow-Up", "Confirmed", "Cancelled", "Completed", "No Show"],
            key="view_status"
        )
    with col4:
        properties = ["All"] + sorted(df["property"].dropna().unique().tolist())
        filter_property = st.selectbox("Filter by Property", properties, key="view_property")

    sort_order = st.radio(
        "Sort by Check-In Date", 
        ["Descending (Newest First)", "Ascending (Oldest First)"], 
        index=0,
        key="view_sort"
    )

    filtered_df = df.copy()
    
    if start_date:
        filtered_df = filtered_df[pd.to_datetime(filtered_df["check_in"]) >= pd.to_datetime(start_date)]
    if end_date:
        filtered_df = filtered_df[pd.to_datetime(filtered_df["check_in"]) <= pd.to_datetime(end_date)]
    if filter_status != "All":
        filtered_df = filtered_df[filtered_df["booking_status"] == filter_status]
    if filter_property != "All":
        filtered_df = filtered_df[filtered_df["property"] == filter_property]

    if sort_order == "Ascending (Oldest First)":
        filtered_df = filtered_df.sort_values(by="check_in", ascending=True)
    else:
        filtered_df = filtered_df.sort_values(by="check_in", ascending=False)

    if filtered_df.empty:
        st.warning("No reservations match the selected filters.")
    else:
        display_columns = [
            "property", "booking_id", "guest_name", "guest_phone", "check_in", "check_out", 
            "room_no", "room_type", "booking_status", "payment_status", "booking_amount", 
            "total_payment_made", "balance_due"
        ]
        st.dataframe(filtered_df[display_columns], use_container_width=True)
