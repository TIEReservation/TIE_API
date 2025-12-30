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
STAYFLEXI_API_BASE_URL = "https://app.stayflexi.com"
STAYFLEXI_EMAIL = "gayathri.tie@gmail.com"

# Property mapping from hotel_id to property name
PROPERTY_MAPPING = {
    "27719": "Le Poshe Beach View",
    "31550": "La Millionaire Luxury Resort",
    "27720": "Le Poshe Luxury",
    "27721": "Le Poshe Suite",
    "27707": "La Paradise Residency",
    "27706": "La Paradise Luxury",
    "27711": "La Villa Heritage",
    "27723": "Le Pondy Beachside",
    "27722": "Le Royce Villa",
    "27709": "La Tamara Luxury",
    "27704": "La Antilia Luxury",
    "27710": "La Tamara Suite",
    "32470": "Le Park Luxury Resort",
    "27724": "Villa Shakti",
    "30357": "Eden Beach Resort",
    "34006": "La Coromandel Luxury",
}

# ========================================================================
# TOKEN MANAGEMENT - Store in session state
# ========================================================================
def get_current_token():
    """Get current token from session state or secrets"""
    if 'stayflexi_api_token' in st.session_state and st.session_state.stayflexi_api_token:
        return st.session_state.stayflexi_api_token
    
    # Try to get from secrets as fallback
    try:
        return st.secrets.get("stayflexi", {}).get("api_token", None)
    except:
        return None

def set_current_token(token: str):
    """Save token to session state"""
    st.session_state.stayflexi_api_token = token

def get_fresh_api_token(email: str, password: str):
    """Get a fresh API token from Stayflexi login endpoint."""
    # ✅ FIXED: Correct URL
    login_url = f"{STAYFLEXI_API_BASE_URL}/auth/login"
    
    if not password:
        return None, "Password is required"
    
    try:
        response = requests.post(
            login_url,
            json={"email": email, "password": password},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        # Check response status
        if response.status_code == 400:
            return None, "Invalid credentials or bad request"
        elif response.status_code == 401:
            return None, "Authentication failed - Invalid email or password"
        
        response.raise_for_status()
        data = response.json()
        
        # Extract token from response
        token = data.get("token") or data.get("accessToken") or data.get("access_token")
        
        if token:
            set_current_token(token)
            return token, None
        else:
            return None, "Token not found in response"
            
    except requests.exceptions.Timeout:
        return None, "Request timeout - please try again"
    except requests.exceptions.RequestException as e:
        return None, f"Network error: {str(e)}"
    except Exception as e:
        return None, f"Unexpected error: {str(e)}"

# ========================================================================
# HELPER FUNCTIONS
# ========================================================================
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

def parse_stayflexi_datetime(datetime_str):
    """Parse Stayflexi date format: '28-12-2025 14:00:00'"""
    if not datetime_str:
        return None
    try:
        return datetime.strptime(datetime_str, "%d-%m-%Y %H:%M:%S").date()
    except:
        try:
            return datetime.strptime(datetime_str[:10], "%d-%m-%Y").date()
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

# ========================================================================
# DATABASE OPERATIONS
# ========================================================================
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

# ========================================================================
# STAYFLEXI API OPERATIONS
# ========================================================================
def fetch_stayflexi_bookings(hotel_id: str, from_date: date, to_date: date):
    """Fetch bookings from Stayflexi API for a specific property and date range."""
    url = f"{STAYFLEXI_API_BASE_URL}/core/api/v1/reservation/navigationGetRoomBookings"
    
    # Get current token
    token = get_current_token()
    
    if not token:
        return {"error": "no_token", "message": "No API token available. Please provide credentials."}
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Query parameters
    params = {
        "hotel_id": hotel_id,
        "hotelId": hotel_id
    }
    
    # POST body payload
    payload = {
        "hotelId": hotel_id,
        "from": from_date.strftime("%Y-%m-%d"),
        "to": to_date.strftime("%Y-%m-%d")
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, params=params, timeout=30)
        
        # Check for 401 Unauthorized - token expired
        if response.status_code == 401:
            return {"error": "unauthorized", "message": "API token expired or invalid"}
        
        response.raise_for_status()
        data = response.json()
        
        # Parse the API structure
        bookings = []
        if isinstance(data, dict) and "allRoomReservations" in data:
            single_room_reservations = data["allRoomReservations"].get("singleRoomReservations", [])
            
            for room_data in single_room_reservations:
                room_id = room_data.get("roomId", "")
                room_type_name = room_data.get("roomTypeName", "")
                res_info_list = room_data.get("resInfoList", [])
                
                for reservation in res_info_list:
                    # Skip blocked rooms
                    if reservation.get("reservationStatus") == "BLOCKED":
                        continue
                    
                    reservation["room_id"] = room_id
                    reservation["room_type_name"] = room_type_name
                    bookings.append(reservation)
            
            return bookings
        else:
            return []
            
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            return {"error": "unauthorized", "message": "API token expired or invalid"}
        return {"error": "http_error", "message": str(e)}
    except requests.exceptions.RequestException as e:
        return {"error": "request_error", "message": str(e)}
    except Exception as e:
        return {"error": "unknown", "message": str(e)}

def transform_stayflexi_to_db_format(booking: dict, property_name: str):
    """Transform Stayflexi booking data to match database schema."""
    guest_name = truncate_string(booking.get("username", ""), 50)
    guest_phone = truncate_string(booking.get("userContact", ""), 50)
    guest_email = booking.get("userEmail", "")
    
    check_in = parse_stayflexi_datetime(booking.get("checkin"))
    check_out = parse_stayflexi_datetime(booking.get("checkout"))
    
    room_no = truncate_string(booking.get("room_id", ""), 50)
    room_type = truncate_string(booking.get("room_type_name", ""), 50)
    
    booking_id = truncate_string(booking.get("bookingId", ""), 50)
    reservation_id = booking.get("reservationId", "")
    booking_source = truncate_string(booking.get("bookingSource", ""), 50)
    segment = truncate_string(booking.get("segment", ""), 50)
    staflexi_status = truncate_string(booking.get("reservationStatus", ""), 50)
    
    room_price = float(booking.get("roomPrice", 0))
    balance_due = float(booking.get("balanceDue", 0))
    
    booking_amount = room_price
    total_payment_made = booking_amount - balance_due if balance_due <= booking_amount else 0
    
    room_nights = 0
    if check_in and check_out:
        room_nights = (check_out - check_in).days
    
    payment_status = calculate_payment_status(total_payment_made, booking_amount)
    
    no_of_adults = 2
    no_of_children = 0
    no_of_infant = 0
    total_pax = no_of_adults
    
    is_group_booking = booking.get("groupBooking", False)
    locked_status = booking.get("lockedStatus", "")
    
    remarks_parts = []
    if guest_email:
        remarks_parts.append(f"Email: {guest_email}")
    if reservation_id:
        remarks_parts.append(f"Reservation ID: {reservation_id}")
    if is_group_booking:
        remarks_parts.append("Group Booking")
    if locked_status == "LOCKED":
        remarks_parts.append("Room Locked")
    
    remarks = truncate_string(" | ".join(remarks_parts), 500)
    
    booking_status = "Confirmed" if staflexi_status == "CONFIRMED" else "Pending"
    
    db_record = {
        "property": property_name,
        "booking_id": booking_id,
        "booking_made_on": None,
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
        "rate_plans": "",
        "booking_source": booking_source,
        "segment": segment,
        "staflexi_status": staflexi_status,
        "booking_confirmed_on": None,
        "booking_amount": booking_amount,
        "total_payment_made": total_payment_made,
        "balance_due": balance_due,
        "mode_of_booking": booking_source,
        "booking_status": booking_status,
        "payment_status": payment_status,
        "remarks": remarks,
        "submitted_by": "Stayflexi API",
        "modified_by": "",
        "total_amount_with_services": 0,
        "ota_gross_amount": 0,
        "ota_commission": 0,
        "ota_tax": 0,
        "ota_net_amount": 0,
        "room_revenue": room_price,
        "room_nights": room_nights,
        "advance_mop": "",
        "balance_mop": "",
        "advance_remarks": "",
        "balance_remarks": "",
        "accounts_status": "Pending"
    }
    
    return db_record

def sync_property_bookings(hotel_id: str, property_name: str, from_date: date, to_date: date, existing_ids: set):
    """Sync bookings for a single property. Returns (inserted, skipped, errors, status)"""
    inserted = 0
    skipped = 0
    errors = 0
    
    api_bookings = fetch_stayflexi_bookings(hotel_id, from_date, to_date)
    
    # Check for errors
    if isinstance(api_bookings, dict) and "error" in api_bookings:
        return inserted, skipped, errors, api_bookings["error"]
    
    if not api_bookings:
        return inserted, skipped, errors, None
    
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
            errors += 1
    
    return inserted, skipped, errors, None

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

# ========================================================================
# MAIN UI
# ========================================================================
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
            if st.button("📤 Sync Excel to Database", key="sync_excel"):
                with st.spinner("Processing and syncing..."):
                    inserted, skipped = process_and_sync_excel(uploaded_file)
                    st.success(f"✅ Synced successfully! Inserted: {inserted}, Skipped (duplicates): {skipped}")
                    st.session_state.online_reservations = load_online_reservations_from_supabase()
    
    # Tab 2: Stayflexi API Sync
    with tab2:
        st.subheader("Sync from Stayflexi API")
        
        # ✅ TOKEN MANAGEMENT SECTION
        st.markdown("### 🔐 API Token Management")
        
        current_token = get_current_token()
        
        if current_token:
            # Show masked token
            masked_token = current_token[:20] + "..." + current_token[-10:] if len(current_token) > 30 else current_token
            st.success(f"✅ Token Active: `{masked_token}`")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 Refresh Token", key="refresh_token_btn"):
                    st.session_state.show_token_input = True
                    st.rerun()
            with col2:
                if st.button("❌ Clear Token", key="clear_token_btn"):
                    set_current_token(None)
                    st.success("Token cleared")
                    st.rerun()
        else:
            st.warning("⚠️ No API token available. Please provide credentials to get a token.")
            st.session_state.show_token_input = True
        
        # Token input form
        if st.session_state.get('show_token_input', False) or not current_token:
            with st.form("token_form"):
                st.markdown("**Enter Stayflexi Credentials:**")
                col1, col2 = st.columns(2)
                with col1:
                    email_input = st.text_input("Email", value=STAYFLEXI_EMAIL)
                with col2:
                    password_input = st.text_input("Password", type="password")
                
                submit_token = st.form_submit_button("🔓 Get API Token")
                
                if submit_token:
                    if email_input and password_input:
                        with st.spinner("Getting API token..."):
                            token, error = get_fresh_api_token(email_input, password_input)
                            if token:
                                st.success("✅ Token obtained successfully!")
                                st.session_state.show_token_input = False
                                st.rerun()
                            else:
                                st.error(f"❌ Failed: {error}")
                    else:
                        st.error("Please provide both email and password")
        
        st.markdown("---")
        
        # Date range selection
        st.markdown("### 📅 Select Date Range")
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
            
            if st.button("🔄 Sync from API", use_container_width=True, type="primary", key="sync_api"):
                # Check if we have a token
                if not get_current_token():
                    st.error("❌ No API token available. Please provide credentials above.")
                elif not sync_all and not selected_properties:
                    st.error("Please select at least one property to sync")
                else:
                    with st.spinner("Syncing bookings from Stayflexi API..."):
                        existing_ids = get_existing_booking_ids()
                        
                        total_inserted = 0
                        total_skipped = 0
                        total_errors = 0
                        property_results = {}
                        auth_error = False
                        no_token_error = False
                        
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
                            
                            inserted, skipped, errors, status = sync_property_bookings(
                                hotel_id, property_name, from_date, to_date, existing_ids
                            )
                            
                            if status == "unauthorized":
                                auth_error = True
                                st.error(f"🔒 Token expired for {property_name}")
                                break
                            elif status == "no_token":
                                no_token_error = True
                                break
                            
                            total_inserted += inserted
                            total_skipped += skipped
                            total_errors += errors
                            
                            property_results[property_name] = {
                                "inserted": inserted,
                                "skipped": skipped,
                                "errors": errors
                            }
                            
                            progress_bar.progress((idx + 1) / total_properties)
                            time.sleep(0.3)
                        
                        progress_bar.empty()
                        status_text.empty()
                        
                        if auth_error:
                            st.error("🔒 **API Token Expired**")
                            st.warning("Click 'Refresh Token' button above to get a new token.")
                            set_current_token(None)  # Clear expired token
                        elif no_token_error:
                            st.error("❌ **No Token Available**")
                            st.warning("Please provide credentials above to get an API token.")
                        else:
                            st.success(f"✅ API Sync Complete!")
                            
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("✅ Inserted", total_inserted)
                            with col2:
                                st.metric("⭐ Skipped", total_skipped)
                            with col3:
                                st.metric("❌ Errors", total_errors)
                            
                            if property_results:
                                st.subheader("Details by Property")
                                results_df = pd.DataFrame.from_dict(property_results, orient='index')
                                results_df = results_df.reset_index()
                                results_df.columns = ["Property", "Inserted", "Skipped", "Errors"]
                                results_df = results_df[(results_df["Inserted"] > 0) | (results_df["Skipped"] > 0) | (results_df["Errors"] > 0)]
                                if not results_df.empty:
                                    st.dataframe(results_df, use_container_width=True, hide_index=True)
                            
                            if 'online_reservations' in st.session_state:
                                del st.session_state.online_reservations
                            st.session_state.online_reservations = load_online_reservations_from_supabase()
                            
                            st.info("💡 Synced bookings will now appear in DMS and can be edited in 'Edit Online Reservations'")
        
        # Info section
        with st.expander("ℹ️ API Sync Information"):
            st.markdown("""
            **How Token Management Works:**
            1. Provide your Stayflexi email and password once
            2. System gets a fresh API token automatically
            3. Token is stored in session (valid for current session)
            4. If token expires during sync, you'll be prompted to refresh
            5. No need to manually extract token from browser!
            
            **How Sync Works:**
            1. Fetches bookings from Stayflexi API for selected date range
            2. Transforms data to match your database schema
            3. Skips duplicate booking IDs automatically
            4. Inserts new bookings with status "Confirmed" or "Pending"
            5. Bookings automatically appear in DMS
            
            **Default Settings:**
            - Booking Status: Automatically set based on Stayflexi status
            - Payment Status: Calculated automatically
            - Submitted By: "Stayflexi API"
            
            **Property Mapping:**
            """)
            mapping_df = pd.DataFrame(
                list(PROPERTY_MAPPING.items()),
                columns=["Hotel ID", "Property Name"]
            )
            st.dataframe(mapping_df, use_container_width=True, hide_index=True)
            
            st.success("""
            ✅ **All 16 Properties Configured!**
            
            All properties are mapped and ready for API sync.
            """)

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
        st.dataframe(filtered_df[display_columns], use_container_width=True, hide_index=True)
